#!/usr/bin/env node
/**
 * Clawbot Zalo Personal Bridge
 *
 * Connects Zalo Personal (via zca-js) to Clawbot's Python backend via WebSocket.
 *
 * Usage:
 *   clawbot-zalo-personal-bridge          # QR-only mode: show QR, save session, exit (no ports)
 *   clawbot-zalo-personal-bridge start    # Daemon mode: start WebSocket server
 *
 * Env: ZALO_PERSONAL_BRIDGE_PORT or BRIDGE_PORT (default 3002), ADMIN_PORT, AUTH_DIR, BRIDGE_TOKEN
 */

import { ZaloBridgeServer } from './server.js';
import { ZaloClient } from './zalo.js';
import { homedir } from 'os';
import { join } from 'path';

const PORT = parseInt(
  process.env.ZALO_PERSONAL_BRIDGE_PORT || process.env.BRIDGE_PORT || '3002',
  10
);
const ADMIN_PORT = process.env.ADMIN_PORT ? parseInt(process.env.ADMIN_PORT, 10) : undefined;
const AUTH_DIR = process.env.AUTH_DIR || join(homedir(), '.clawbot', 'zalo-auth');
const TOKEN = process.env.BRIDGE_TOKEN || undefined;

const subcommand = process.argv[2];

console.log('🐈 Clawbot Zalo Personal Bridge');
console.log('==============================\n');

if (!subcommand) {
  // QR-only mode: connect, print QR to terminal, exit after auth (no ports)
  const za = new ZaloClient({
    authDir: AUTH_DIR,
    onMessage: () => {},
    onQR: () => {},
    onStatus: (status) => {
      if (status === 'connected') {
        console.log('✅ Session saved. You can close this terminal and start the bridge with: clawbot-zalo-personal-bridge start');
        process.exit(0);
      }
    },
  });
  // connect() resolves after QR scan; connected event fires shortly after
  za.connect()
    .then(() => {
      // Keep process alive until onStatus('connected') triggers exit
      setTimeout(() => {
        console.error('Timed out waiting for connected event after QR scan');
        process.exit(1);
      }, 30_000).unref();
    })
    .catch((err) => {
      console.error('Failed to connect:', err);
      process.exit(1);
    });
} else if (subcommand === 'start') {
  // Daemon mode: WebSocket server + admin HTTP
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
} else {
  console.error(`Unknown subcommand: ${subcommand}`);
  console.error('Usage: clawbot-zalo-personal-bridge [start]');
  process.exit(1);
}
