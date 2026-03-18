#!/usr/bin/env node
/**
 * Clawbot WhatsApp Bridge
 *
 * This bridge connects WhatsApp Web to Clawbot's Python backend
 * via WebSocket. It handles authentication, message forwarding,
 * and reconnection logic.
 *
 * Usage:
 *   clawbot-whatsapp-bridge          # QR-only mode: show QR, save session, exit (no ports)
 *   clawbot-whatsapp-bridge start    # Daemon mode: start WebSocket server (used by post_install)
 *
 * Env: WHATSAPP_BRIDGE_PORT (3001), AUTH_DIR, BRIDGE_TOKEN
 */

// Polyfill crypto for Baileys in ESM
import { webcrypto } from 'crypto';
if (!globalThis.crypto) {
  (globalThis as any).crypto = webcrypto;
}

import { BridgeServer } from './server.js';
import { WhatsAppClient } from './whatsapp.js';
import { homedir } from 'os';
import { join } from 'path';

const PORT = parseInt(
  process.env.WHATSAPP_BRIDGE_PORT || process.env.BRIDGE_PORT || '3001',
  10
);
const ADMIN_PORT = process.env.ADMIN_PORT ? parseInt(process.env.ADMIN_PORT, 10) : undefined;
const AUTH_DIR = process.env.AUTH_DIR || join(homedir(), '.clawbot', 'whatsapp-auth');
const TOKEN = process.env.BRIDGE_TOKEN || undefined;

const subcommand = process.argv[2];

console.log('🐈 Clawbot WhatsApp Bridge');
console.log('========================\n');

if (!subcommand) {
  // QR-only mode: connect, print QR to terminal, exit after auth (no ports)
  const wa = new WhatsAppClient({
    authDir: AUTH_DIR,
    onMessage: () => {},
    onQR: () => {},
    onStatus: () => {},
    exitOnConnect: true,
  });
  wa.connect().catch((err) => {
    console.error('Failed to connect:', err);
    process.exit(1);
  });
} else if (subcommand === 'start') {
  // Daemon mode: WebSocket server + admin HTTP
  const server = new BridgeServer(PORT, AUTH_DIR, TOKEN, ADMIN_PORT);

  process.on('SIGINT', async () => {
    console.log('\n\nShutting down...');
    await server.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    await server.stop();
    process.exit(0);
  });

  server.start().catch((error) => {
    console.error('Failed to start bridge:', error);
    process.exit(1);
  });
} else {
  console.error(`Unknown subcommand: ${subcommand}`);
  console.error('Usage: clawbot-whatsapp-bridge [start]');
  process.exit(1);
}
