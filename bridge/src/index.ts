#!/usr/bin/env node
/**
 * MathClaw WhatsApp Bridge
 * 
 * This bridge connects WhatsApp Web to MathClaw's Python backend
 * via WebSocket. It handles authentication, message forwarding,
 * and reconnection logic.
 * 
 * Usage:
 *   npm run build && npm start
 *   
 * Or with custom settings:
 *   BRIDGE_PORT=3001 AUTH_DIR=~/.mathclaw/whatsapp-auth npm start
 */

// Polyfill crypto for Baileys in ESM
import { webcrypto } from 'crypto';
if (!globalThis.crypto) {
  (globalThis as any).crypto = webcrypto;
}

import { BridgeServer } from './server.js';
import { existsSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

const PORT = parseInt(process.env.BRIDGE_PORT || '3001', 10);
const DEFAULT_AUTH_DIR = (() => {
  const preferred = join(homedir(), '.mathclaw', 'whatsapp-auth');
  const legacy = join(homedir(), '.nanobot', 'whatsapp-auth');
  return existsSync(preferred) || !existsSync(legacy) ? preferred : legacy;
})();
const AUTH_DIR = process.env.AUTH_DIR || DEFAULT_AUTH_DIR;
const TOKEN = process.env.BRIDGE_TOKEN || undefined;

console.log('?? MathClaw WhatsApp Bridge');
console.log('========================\n');

const server = new BridgeServer(PORT, AUTH_DIR, TOKEN);

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
