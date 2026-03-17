/**
 * Zalo Personal client wrapper using zca-js.
 * Based on OpenClaw's zalouser implementation.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import { Zalo, ThreadType, LoginQRCallbackEventType } from 'zca-js';
import qrcode from 'qrcode-terminal';

export interface ZaloInboundMessage {
  id: string;
  sender: string;
  threadId: string;
  threadType: 'user' | 'group';
  content: string;
  timestamp: number;
  isGroup: boolean;
}

export interface ZaloClientOptions {
  authDir: string;
  onMessage: (msg: ZaloInboundMessage) => void;
  onQR: (qr: string, refresh?: () => void) => void;
  onStatus: (status: string) => void;
}

export class ZaloClient {
  private api: any = null;
  private options: ZaloClientOptions;
  private reconnecting = false;

  constructor(options: ZaloClientOptions) {
    this.options = options;
  }

  async connect(): Promise<void> {
    const zalo = new Zalo();
    this.api = await zalo.loginQR(
      { qrPath: undefined },
      (event: any) => {
        if (event.type === LoginQRCallbackEventType.QRCodeGenerated && event.data?.code) {
          console.log('\n📱 Scan this QR code with Zalo:\n');
          qrcode.generate(event.data.code, { small: true });
          const retryFn = event.actions?.retry ? () => event.actions.retry() : undefined;
          this.options.onQR(event.data.code, retryFn);
          event.actions?.saveToFile?.();
        } else if (event.type === LoginQRCallbackEventType.QRCodeExpired) {
          event.actions?.retry?.();
        }
      }
    );

    this.api.listener.on('connected', () => {
      console.log('✅ Connected to Zalo');
      this.options.onStatus('connected');
    });

    this.api.listener.on('message', (message: any) => {
      const content = message.data?.content;
      const isPlainText = typeof content === 'string';
      if (message.isSelf || !isPlainText) return;

      const threadType = message.type === ThreadType.Group ? 'group' : 'user';
      const threadId = String(message.threadId || '');
      const sender = String(message.data?.uidFrom || message.threadId || threadId);

      this.options.onMessage({
        id: message.data?.msgId || `${Date.now()}`,
        sender,
        threadId,
        threadType,
        content: content || '',
        timestamp: parseInt(message.data?.ts, 10) || Date.now(),
        isGroup: threadType === 'group',
      });
    });

    this.api.listener.on('disconnected', (code: number, reason: string) => {
      console.log(`Zalo disconnected: ${code} ${reason}`);
      this.options.onStatus('disconnected');
      if (!this.reconnecting) {
        this.reconnecting = true;
        console.log('Reconnecting in 5 seconds...');
        setTimeout(() => {
          this.reconnecting = false;
          this.connect();
        }, 5000);
      }
    });

    this.api.listener.start();
  }

  async sendMessage(threadId: string, threadType: 'user' | 'group', text: string): Promise<void> {
    if (!this.api) {
      throw new Error('Not connected');
    }
    const type = threadType === 'group' ? ThreadType.Group : ThreadType.User;
    await this.api.sendMessage({ msg: text }, threadId, type);
  }

  async disconnect(): Promise<void> {
    if (this.api?.listener) {
      this.api.listener.stop?.();
    }
    this.api = null;
  }
}
