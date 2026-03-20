──────────────────────────────────────
PLUGIN SPEC COMPLIANCE CHECK
moses-governance vs Official Claude Code Plugin Reference
2026-03-07
──────────────────────────────────────

## MANIFEST (plugin.json)

| Field | Spec | Ours | Status |
|-------|------|------|--------|
| name | Required | ✓ "moses-governance" | OK |
| version | Optional | ✓ "1.0.0" | OK |
| description | Optional | ✓ | OK |
| author.name | Optional | ✓ "Ello Cello LLC" | OK |
| author.email | Optional | ✓ | OK |
| author.url | Optional | ✓ | OK |
| homepage | Optional | ✓ mos2es.io | OK |
| repository | Optional | ✓ | OK |
| license | Optional | ✓ | OK |
| keywords | Optional | ✓ 10 keywords | OK |
| commands | Optional | ✓ "./commands/" | OK |
| agents | Optional | ✓ "./agents/" | OK |
| skills | Optional | ✓ "./skills/" | OK |
| hooks | Optional | ✓ "./hooks/hooks.json" | OK |
| mcpServers | Optional | ✗ Not included | **GAP** |
| outputStyles | Optional | ✗ Not included | SKIP (not relevant) |
| lspServers | Optional | ✗ Not included | SKIP (not relevant) |
| categories | Not in spec | ✓ We have it | Remove or keep (won't break anything) |

### GAP: mcpServers
We don't have an MCP server config. This is optional, but for a governance plugin that's meant to wrap agent operations, having an MCP server that agents can connect to for governance checks would be the execution layer. This maps directly to the MCP bridge from the COMMAND build recipe.

**Decision:** Not needed for initial plugin submission. The governance works through skills and hooks without MCP. MCP server can be added in v1.1 when the backend is built.

---

## DIRECTORY STRUCTURE

Official enterprise example from the docs:
```
enterprise-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
├── agents/
├── skills/
│   ├── code-reviewer/
│   │   └── SKILL.md
│   └── pdf-processor/
│       ├── SKILL.md
│       └── scripts/
├── hooks/
│   ├── hooks.json
│   └── security-hooks.json
├── settings.json          ← WE DON'T HAVE THIS
├── .mcp.json              ← WE DON'T HAVE THIS
├── .lsp.json              ← NOT RELEVANT
├── scripts/
├── LICENSE
└── CHANGELOG.md           ← WE DON'T HAVE THIS
```

| Component | Official | Ours | Status |
|-----------|----------|------|--------|
| .claude-plugin/plugin.json | ✓ | ✓ | OK |
| .claude-plugin/marketplace.json | ✓ | ✓ | OK |
| commands/*.md | ✓ | ✓ 9 commands | OK |
| agents/*.md | ✓ | ✓ 3 agents | OK |
| skills/*/SKILL.md | ✓ | ✓ 6 skills | OK |
| hooks/hooks.json | ✓ | ✓ | OK |
| hooks/*.sh (scripts) | ✓ | ✓ 2 scripts | OK |
| scripts/ | ✓ | ✓ governance.py + audit.py | OK |
| settings.json | ✓ | ✗ **MISSING** | **GAP** |
| .mcp.json | ✓ | ✗ Not needed yet | DEFER |
| CHANGELOG.md | ✓ | ✗ **MISSING** | **GAP** |
| LICENSE | ✓ | ✓ LICENSE.md | OK |
| README.md | ✓ | ✓ | OK |
| CLAUDE.md | Not required | ✓ (bonus) | OK |
| NOTICE.md | Not required | ✓ (bonus) | OK |
| docs/ | Not required | ✓ (bonus) | OK |
| examples/ | Not required | ✓ (bonus) | OK |
| references/ | Not required | ✓ (bonus) | OK |
| contexts/ | Not required | ✓ (bonus) | OK |
| rules/ | Not required | ✓ (bonus) | OK |
| assets/ | Not required | ✓ (bonus) | OK |

---

## GAPS TO FIX

### 1. settings.json (MISSING)
The official spec shows plugins can include a `settings.json` that applies default settings when the plugin is enabled. For a governance plugin, this is where we'd set default behaviors.

Recommended content:
```json
{
  "preferences": {
    "governance_mode": "None (Unrestricted)",
    "posture": "SCOUT",
    "role": "Primary"
  }
}
```

This gives every user sane defaults on install — unrestricted mode (so it's not invasive out of the box) but SCOUT posture (read-only by default, requiring explicit opt-in to execution).

### 2. CHANGELOG.md (MISSING)
Standard for any versioned software. Easy to add.

### 3. $ARGUMENTS support in skills
The spec shows skills can accept user input via `$ARGUMENTS` placeholder. Our slash commands handle arguments in their descriptions but we should verify our skills support this pattern where relevant.

For example, `/moses-governance:governance-mode High Security` should work if the skill uses $ARGUMENTS.

### 4. disable-model-invocation flag
The spec shows skills can have `disable-model-invocation: true` in frontmatter to prevent Claude from auto-activating them — they only fire when explicitly invoked. Our governance skills SHOULD auto-activate (that's the whole point), so we should NOT set this flag. But we should be aware it exists in case we add utility skills later that shouldn't auto-fire.

### 5. Hook script path references
Official spec uses `${CLAUDE_PLUGIN_ROOT}` for portable paths in hooks.json. Our hooks.json already uses this. ✓ Confirmed correct.

### 6. Marketplace source field
Our marketplace.json uses `"source": "."` which means the plugin lives in the same directory as the marketplace file. This is correct for a self-contained repo. If we later separate the marketplace from the plugin, the source would change to a subdirectory path.

---

## WHAT WE HAVE THAT THE SPEC DOESN'T REQUIRE (OVERSHOOT)

These are bonus components that go beyond the official spec:

| Component | What It Is | Why It Overshoots |
|-----------|-----------|-------------------|
| contexts/ | Mode-specific context files | No other plugin has behavioral mode contexts |
| rules/ | Always-follow governance rules | Constitutional constraints, not just guidelines |
| references/ | Mode, role, posture specs | Progressive disclosure reference docs |
| assets/governance-schema.json | Governed context payload schema | Formal API contract for governance |
| docs/ARCHITECTURE.md | System design doc | Enterprise-grade documentation |
| docs/ENTERPRISE-USE.md | Enterprise deployment patterns | Targeted at enterprise buyers |
| docs/PATENT-NOTICE.md | IP documentation | Patent-backed, not just a weekend project |
| docs/QUICKSTART.md | 5-minute guide | Onboarding experience |
| examples/ (4 scenarios) | Worked governance examples | Shows real-world application |
| CLAUDE.md | Project north star | Best practice from ECC pattern |
| NOTICE.md | IP attribution | Legal completeness |

---

## FINAL ACTION ITEMS

1. **Add settings.json** — default governance settings on install
2. **Add CHANGELOG.md** — version history
3. **Verify $ARGUMENTS** — confirm slash commands pass user input correctly
4. **Done.** Everything else is either compliant or intentional overshoot.
