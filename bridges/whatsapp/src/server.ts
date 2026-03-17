/**
 * WebSocket server for Python-Node.js bridge communication.
 * Security: binds to 127.0.0.1 only; optional BRIDGE_TOKEN auth.
 *
 * Admin HTTP API (on adminPort, default wsPort+1):
 *   GET  /admin/qr          – returns { qr, timestamp } or 404 if no QR yet
 *   POST /admin/qr/refresh  – triggers a new QR code generation
 */

import { createServer, IncomingMessage, ServerResponse, Server as HttpServer } from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import { WhatsAppClient, InboundMessage } from './whatsapp.js';

interface SendCommand {
  type: 'send';
  to: string;
  text: string;
}

interface BridgeMessage {
  type: 'message' | 'status' | 'qr' | 'error';
  [key: string]: unknown;
}

export class BridgeServer {
  private wss: WebSocketServer | null = null;
  private adminHttp: HttpServer | null = null;
  private wa: WhatsAppClient | null = null;
  private clients: Set<WebSocket> = new Set();

  private latestQR: string | null = null;
  private latestQRTimestamp: number | null = null;
  private refreshQR: (() => void) | null = null;

  constructor(
    private port: number,
    private authDir: string,
    private token?: string,
    private adminPort?: number,
  ) {}

  async start(): Promise<void> {
    // Bind to localhost only — never expose to external network
    this.wss = new WebSocketServer({ host: '127.0.0.1', port: this.port });
    console.log(`🌉 Bridge server listening on ws://127.0.0.1:${this.port}`);
    if (this.token) console.log('🔒 Token authentication enabled');

    // Initialize WhatsApp client
    this.wa = new WhatsAppClient({
      authDir: this.authDir,
      onMessage: (msg: InboundMessage) => this.broadcast({ type: 'message', ...msg }),
      onQR: (qr: string, refresh?: () => void) => {
        this.latestQR = qr;
        this.latestQRTimestamp = Date.now();
        if (refresh) this.refreshQR = refresh;
        this.broadcast({ type: 'qr', qr });
      },
      onStatus: (status: string) => this.broadcast({ type: 'status', status }),
    });

    // Handle WebSocket connections
    this.wss.on('connection', (ws) => {
      if (this.token) {
        // Require auth handshake as first message
        const timeout = setTimeout(() => ws.close(4001, 'Auth timeout'), 5000);
        ws.once('message', (data) => {
          clearTimeout(timeout);
          try {
            const msg = JSON.parse(data.toString());
            if (msg.type === 'auth' && msg.token === this.token) {
              console.log('🔗 Python client authenticated');
              this.setupClient(ws);
            } else {
              ws.close(4003, 'Invalid token');
            }
          } catch {
            ws.close(4003, 'Invalid auth message');
          }
        });
      } else {
        console.log('🔗 Python client connected');
        this.setupClient(ws);
      }
    });

    this.startAdminServer();
    await this.wa.connect();
  }

  private isAdminAuthorized(req: IncomingMessage): boolean {
    if (!this.token) return true;
    const auth = req.headers['authorization'];
    if (auth && auth.startsWith('Bearer ') && auth.slice(7) === this.token) return true;
    const url = new URL(req.url || '/', `http://127.0.0.1`);
    if (url.searchParams.get('token') === this.token) return true;
    return false;
  }

  private sendJson(res: ServerResponse, status: number, body: unknown, cors = true): void {
    const payload = JSON.stringify(body);
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Content-Length': String(Buffer.byteLength(payload)),
    };
    if (cors) {
      headers['Access-Control-Allow-Origin'] = '*';
      headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS';
      headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type';
    }
    res.writeHead(status, headers);
    res.end(payload);
  }

  private startAdminServer(): void {
    const adminPort = this.adminPort ?? this.port + 1;

    this.adminHttp = createServer((req, res) => {
      if (req.method === 'OPTIONS') {
        res.writeHead(204, {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type',
          'Access-Control-Max-Age': '86400',
        });
        res.end();
        return;
      }

      if (!this.isAdminAuthorized(req)) {
        this.sendJson(res, 401, { error: 'Unauthorized' });
        return;
      }

      const url = new URL(req.url || '/', `http://127.0.0.1`);
      const path = url.pathname;

      if (req.method === 'GET' && path === '/admin/qr') {
        if (!this.latestQR) {
          this.sendJson(res, 404, { error: 'No QR code available yet' });
        } else {
          this.sendJson(res, 200, { qr: this.latestQR, timestamp: this.latestQRTimestamp });
        }
        return;
      }

      if (req.method === 'POST' && path === '/admin/qr/refresh') {
        if (this.refreshQR) {
          this.refreshQR();
          this.sendJson(res, 200, { ok: true, message: 'QR refresh triggered' });
        } else {
          this.sendJson(res, 503, { error: 'Refresh not available (already authenticated or QR not started)' });
        }
        return;
      }

      this.sendJson(res, 404, { error: 'Not found' });
    });

    this.adminHttp.listen(adminPort, '127.0.0.1', () => {
      console.log(`🛠️  Admin API listening on http://127.0.0.1:${adminPort}`);
      console.log(`   GET  http://127.0.0.1:${adminPort}/admin/qr`);
      console.log(`   POST http://127.0.0.1:${adminPort}/admin/qr/refresh`);
    });
  }

  private setupClient(ws: WebSocket): void {
    this.clients.add(ws);

    ws.on('message', async (data) => {
      try {
        const cmd = JSON.parse(data.toString()) as SendCommand;
        await this.handleCommand(cmd);
        ws.send(JSON.stringify({ type: 'sent', to: cmd.to }));
      } catch (error) {
        console.error('Error handling command:', error);
        ws.send(JSON.stringify({ type: 'error', error: String(error) }));
      }
    });

    ws.on('close', () => {
      console.log('🔌 Python client disconnected');
      this.clients.delete(ws);
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      this.clients.delete(ws);
    });
  }

  private async handleCommand(cmd: SendCommand): Promise<void> {
    if (cmd.type === 'send' && this.wa) {
      await this.wa.sendMessage(cmd.to, cmd.text);
    }
  }

  private broadcast(msg: BridgeMessage): void {
    const data = JSON.stringify(msg);
    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(data);
      }
    }
  }

  async stop(): Promise<void> {
    for (const client of this.clients) {
      client.close();
    }
    this.clients.clear();

    if (this.wss) {
      this.wss.close();
      this.wss = null;
    }

    if (this.adminHttp) {
      this.adminHttp.close();
      this.adminHttp = null;
    }

    if (this.wa) {
      await this.wa.disconnect();
      this.wa = null;
    }
  }
}
