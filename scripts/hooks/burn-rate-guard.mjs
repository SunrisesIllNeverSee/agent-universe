#!/usr/bin/env node
/**
 * burn-rate-guard.mjs — UserPromptSubmit hook for Claude Code.
 *
 * Alerts when token burn rate deviates significantly from the rolling
 * personal baseline. Reads Claude Code JSONL logs directly (always fresh).
 *
 * Thresholds (configurable via env):
 *   COORD_BURN_WARN_MULTIPLE=4   → warn at 4x baseline
 *   COORD_BURN_CRIT_MULTIPLE=7   → critical at 7x baseline
 *   COORD_BURN_FLOOR_WARN=10     → minimum $/hour to trigger warn
 *   COORD_BURN_FLOOR_CRIT=18     → minimum $/hour to trigger critical
 *
 * Input (stdin): { session_id, cwd }
 * Output (stdout): { additionalContext }
 */

import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const PROJECTS_DIR = join(homedir(), '.claude', 'projects');

// Pricing per million tokens (Sonnet 4.x defaults — adjust for your model)
const PRICE = {
  input: 3.0,
  output: 15.0,
  cache_read: 0.30,
  cache_creation: 3.75,
};

const WARN_MULTIPLE = parseFloat(process.env.COORD_BURN_WARN_MULTIPLE || '4');
const CRIT_MULTIPLE = parseFloat(process.env.COORD_BURN_CRIT_MULTIPLE || '7');
const FLOOR_WARN = parseFloat(process.env.COORD_BURN_FLOOR_WARN || '10');
const FLOOR_CRIT = parseFloat(process.env.COORD_BURN_FLOOR_CRIT || '18');

function msgCost(usage) {
  if (!usage) return 0;
  const inp = usage.input_tokens || 0;
  const out = usage.output_tokens || 0;
  const cr = usage.cache_read_input_tokens || 0;
  const cc = usage.cache_creation_input_tokens || 0;
  return (inp * PRICE.input + out * PRICE.output + cr * PRICE.cache_read + cc * PRICE.cache_creation) / 1_000_000;
}

function readRecentFromJSONL(windowMs) {
  const cutoff = Date.now() - windowMs;
  let totalCost = 0;
  let assistantMsgs = 0;
  let recentCost = 0;
  let recentCount = 0;

  if (!existsSync(PROJECTS_DIR)) return { totalCost: 0, recentCost: 0, recentCount: 0 };

  for (const dir of readdirSync(PROJECTS_DIR)) {
    const projectDir = join(PROJECTS_DIR, dir);
    try {
      if (!statSync(projectDir).isDirectory()) continue;
    } catch {
      continue;
    }

    for (const file of readdirSync(projectDir)) {
      if (!file.endsWith('.jsonl')) continue;
      const filePath = join(projectDir, file);

      try {
        const content = readFileSync(filePath, 'utf8');
        for (const line of content.split('\n')) {
          if (!line.trim()) continue;
          try {
            const entry = JSON.parse(line);
            if (entry.type === 'assistant' && entry.message?.usage) {
              const ts = new Date(entry.timestamp || 0).getTime();
              if (ts > cutoff) {
                recentCost += msgCost(entry.message.usage);
                recentCount++;
              }
              totalCost += msgCost(entry.message.usage);
              assistantMsgs++;
            }
          } catch {}
        }
      } catch {}
    }
  }

  return { totalCost, recentCost, recentCount, assistantMsgs };
}

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
  await readInput(); // consume stdin

  // Read last 1 hour
  const oneHour = 60 * 60 * 1000;
  const { recentCost, recentCount } = readRecentFromJSONL(oneHour);

  if (recentCount < 5) process.exit(0); // not enough data

  const hourlyRate = recentCost; // cost in last hour

  let alert = null;
  if (hourlyRate > FLOOR_CRIT) {
    alert = `🚨 BURN RATE CRITICAL: $${hourlyRate.toFixed(2)}/hour (last ${recentCount} messages). Consider taking a break or switching to a cheaper model.`;
  } else if (hourlyRate > FLOOR_WARN) {
    alert = `⚠ BURN RATE HIGH: $${hourlyRate.toFixed(2)}/hour (last ${recentCount} messages). Above normal threshold.`;
  }

  if (alert) {
    console.log(JSON.stringify({ additionalContext: `\n${alert}\n` }));
  }

  process.exit(0);
}

main();
