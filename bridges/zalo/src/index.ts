#!/usr/bin/env node
/**
 * Clawbot Zalo Personal Bridge
 *
 * Connects Zalo Personal (via zca-js) to Clawbot's Python backend via WebSocket.
 *
 * Usage:
 *   npm run build && npm start
 *
 * Env: ZALO_PERSONAL_BRIDGE_PORT or BRIDGE_PORT (default 3002), ADMIN_PORT, AUTH_DIR, BRIDGE_TOKEN
 */

import { ZaloBridgeServer } from './server.js';
import { homedir } from 'os';
import { join } from 'path';

const PORT = parseInt(
  process.env.ZALO_PERSONAL_BRIDGE_PORT || process.env.BRIDGE_PORT || '3002',
  10
);
const ADMIN_PORT = process.env.ADMIN_PORT ? parseInt(process.env.ADMIN_PORT, 10) : undefined;
const AUTH_DIR = process.env.AUTH_DIR || join(homedir(), '.clawbot', 'zalo-auth');
const TOKEN = process.env.BRIDGE_TOKEN || undefined;

console.log('🐈 Clawbot Zalo Personal Bridge');
console.log('==============================\n');

const server = new ZaloBridgeServer(PORT, AUTH_DIR, TOKEN, ADMIN_PORT);

process.on('SIGINT', async () => {
  console.log('\nShutting down...');
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
