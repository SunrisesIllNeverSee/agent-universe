#!/usr/bin/env node
/**
 * pre-tool-use.mjs — PreToolUse hook for Claude Code.
 *
 * Checks .agents/locks.json before any Write/Edit operation.
 * If the file is locked by another session, warns (advisory) or blocks (strict).
 *
 * Configure via env:
 *   COORD_STRICT_LOCKS=1  → exit 2 (blocks the write)
 *   (default)             → exit 0 with warning context (advisory)
 *
 * Input (stdin): { tool_name, tool_input: { file_path }, session_id }
 * Output (stdout): { error or additionalContext }
 */

import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const STRICT = process.env.COORD_STRICT_LOCKS === '1';

function readInput() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.on('data', (c) => (data += c));
    process.stdin.on('end', () => {
      try { resolve(JSON.parse(data)); }
      catch { resolve({}); }
    });
  });
}

async function main() {
  const input = await readInput();
  const toolName = input.tool_name || '';

  // Only check Write/Edit operations
  if (toolName !== 'Write' && toolName !== 'Edit') {
    process.exit(0);
  }

  const filePath = input.tool_input?.file_path || input.tool_input?.filePath || '';
  if (!filePath) process.exit(0);

  // Find repo root
  const scriptDir = dirname(fileURLToPath(import.meta.url));
  const repoRoot = scriptDir.replace(/\/scripts\/hooks$/, '');
  const locksPath = join(repoRoot, '.agents', 'locks.json');

  if (!existsSync(locksPath)) process.exit(0);

  let locks;
  try {
    locks = JSON.parse(readFileSync(locksPath, 'utf8'));
  } catch {
    process.exit(0);
  }

  const lockEntries = locks.locks || {};
  const sessionId = input.session_id || 'unknown';

  // Check if any lock covers this path
  for (const [lockPath, lock] of Object.entries(lockEntries)) {
    if (!lock || typeof lock !== 'object') continue;

    // Check if the file path matches or is under the locked path
    const isMatch = filePath.includes(lockPath) || lockPath.includes(filePath);
    if (!isMatch) continue;

    // Check if lock is expired
    if (lock.expires_at) {
      const expires = new Date(lock.expires_at);
      if (expires < new Date()) continue; // lock expired, skip
    }

    // Check if it's our own lock
    if (lock.claimed_by === sessionId) continue;

    // Someone else has a lock
    const msg = `⚠ File ${lockPath} is locked by ${lock.claimed_by} (reason: ${lock.reason || 'unknown'}). Expires: ${lock.expires_at || 'never'}`;

    if (STRICT) {
      console.log(JSON.stringify({ error: msg }));
      process.exit(2); // block the write
    } else {
      console.log(JSON.stringify({ additionalContext: `\n${msg}\n` }));
      process.exit(0); // advisory only
    }
  }

  process.exit(0);
}

main();
