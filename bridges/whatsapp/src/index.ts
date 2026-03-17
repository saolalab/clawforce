#!/usr/bin/env node
/**
 * Clawbot WhatsApp Bridge
 *
 * This bridge connects WhatsApp Web to Clawbot's Python backend
 * via WebSocket. It handles authentication, message forwarding,
 * and reconnection logic.
 * 
 * Usage:
 *   npm run build && npm start
 *   
 * Or with custom settings:
 *   WHATSAPP_BRIDGE_PORT=3001 AUTH_DIR=/path/to/workspace/data/whatsapp npm start
 */

// Polyfill crypto for Baileys in ESM
import { webcrypto } from 'crypto';
if (!globalThis.crypto) {
  (globalThis as any).crypto = webcrypto;
}

import { BridgeServer } from './server.js';
import { homedir } from 'os';
import { join } from 'path';

const PORT = parseInt(
  process.env.WHATSAPP_BRIDGE_PORT || process.env.BRIDGE_PORT || '3001',
  10
);
const ADMIN_PORT = process.env.ADMIN_PORT ? parseInt(process.env.ADMIN_PORT, 10) : undefined;
const AUTH_DIR = process.env.AUTH_DIR || join(homedir(), '.clawbot', 'whatsapp-auth');
const TOKEN = process.env.BRIDGE_TOKEN || undefined;

console.log('🐈 Clawbot WhatsApp Bridge');
console.log('========================\n');

const server = new BridgeServer(PORT, AUTH_DIR, TOKEN, ADMIN_PORT);

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n\nShutting down...');
  await server.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await server.stop();
  process.exit(0);
});

// Start the server
server.start().catch((error) => {
  console.error('Failed to start bridge:', error);
  process.exit(1);
});
