#!/usr/bin/env node
/**
 * check-okf.mjs — lint the OKF frontmatter convention on every Devins_Plans/*.md.
 *
 * Spec: Devins_Plans/OKF.md (Object-Knowledge Format v0.1). Every doc must open
 * with YAML frontmatter carrying five fields: type, title, description, tags,
 * timestamp. `index.md` additionally carries okf_version (the bundle root).
 *
 * Dependency-free (hand-parses the flat frontmatter — no YAML lib needed).
 *   node scripts/check-okf.mjs        exit 0 = all compliant, 1 = violations
 */

import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'Devins_Plans')

const TYPES = new Set([
  'Design', 'Brief', 'Spec', 'Reference', 'Analysis', 'Runbook',
  'Coordination', 'Roadmap', 'Findings', 'Roster', 'Index',
])
const REQUIRED = ['type', 'title', 'description', 'tags', 'timestamp']

/** Extract the frontmatter block (raw lines) or null if absent. */
function frontmatter(text) {
  const lines = text.split('\n')
  if (lines[0].trim() !== '---') return null
  const end = lines.indexOf('---', 1)
  if (end === -1) return null
  return lines.slice(1, end)
}

/** Parse flat `key: value` frontmatter lines into a map (top-level keys only). */
function parse(block) {
  const obj = {}
  for (const line of block) {
    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s?(.*)$/)
    if (m) obj[m[1]] = m[2].trim()
  }
  return obj
}

// Recurse into topic folders (onboarding/, auth-profile/, reference/**, etc.) so foldered
// docs stay gated. Skip frozen/historical trees — they predate the convention.
const SKIP_DIRS = new Set(['_archive', '_planning', '_merge', 'sigrank-agent'])
function walk(dir, rel = '') {
  const out = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (SKIP_DIRS.has(e.name)) continue
      out.push(...walk(join(dir, e.name), rel ? `${rel}/${e.name}` : e.name))
    } else if (e.name.endsWith('.md')) {
      out.push(rel ? `${rel}/${e.name}` : e.name)
    }
  }
  return out
}
const files = walk(DIR).sort()
const violations = []

for (const f of files) {
  const text = readFileSync(join(DIR, f), 'utf8')
  const block = frontmatter(text)
  if (!block) {
    violations.push([f, 'no frontmatter (missing opening `---` block)'])
    continue
  }
  const fm = parse(block)
  const missing = REQUIRED.filter((k) => !fm[k] || fm[k] === '')
  if (missing.length) violations.push([f, `missing field(s): ${missing.join(', ')}`])
  if (fm.type && !TYPES.has(fm.type)) violations.push([f, `type "${fm.type}" not in vocabulary`])
  if (fm.tags) {
    const tags = fm.tags.replace(/^\[|\]$/g, '').split(',').map((t) => t.trim().replace(/^["']|["']$/g, '')).filter(Boolean)
    if (tags.length < 1) violations.push([f, `tags must be a non-empty list (got: ${fm.tags})`])
  }
  if (fm.timestamp && !/^\d{4}-\d{2}-\d{2}/.test(fm.timestamp)) {
    violations.push([f, `timestamp "${fm.timestamp}" not YYYY-MM-DD`])
  }
  if (f === 'index.md' && !fm.okf_version) violations.push([f, 'index root missing okf_version'])
}

const compliant = files.length - new Set(violations.map((v) => v[0])).size
if (violations.length === 0) {
  console.log(`✓ OKF: all ${files.length} Devins_Plans/*.md docs compliant.`)
  process.exit(0)
}
console.log(`✗ OKF: ${compliant}/${files.length} compliant — ${violations.length} violation(s):\n`)
for (const [f, why] of violations) console.log(`  ${f.padEnd(34)} ${why}`)
process.exit(1)
