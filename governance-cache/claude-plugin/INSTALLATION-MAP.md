# Document Numbering System — Installation Map

Where each file goes for each environment.

## claude.ai (Web / Mobile)

**Mechanism:** Memory edits (already installed)
**Files:** None needed — memory edits #4 and #5 fire automatically
**Coverage:** ~85% — core rules + formatting, may drift on edge cases in very long threads
**Nothing to install.** Already active.

## Claude Code (CLI)

**Mechanism:** CLAUDE.md at project root + plugin
**Files to place:**
```
your-project/
└── CLAUDE.md          ← copy from environment-configs/CLAUDE.md
```
**Plugin (for full governance suite):**
```
~/.claude/plugins/moses-governance/   ← entire plugin/ folder
```
**Coverage:** 100% — full spec, auto-activating skill, /docs command, hooks

## Cowork (Desktop Agent)

**Mechanism:** Global Instructions + memory.md in working folder
**Setup:**
1. Go to Settings → Cowork → Global Instructions
2. Paste contents of `cowork-global-instructions.md`
3. Drop `cowork-memory.md` into your Cowork working folder as `memory.md`

**Coverage:** 100% — full spec fires on every session, memory.md adds project context

## Claude Code + Cowork Together

If using both:
- CLAUDE.md in project root (for CLI sessions)
- Global Instructions in Cowork settings (for Cowork sessions)
- memory.md in working folder (for persistent context in both)
- Plugin installed for the full governance suite

No conflicts. They complement — CLAUDE.md is project-scoped, Global Instructions is global, memory.md is workspace-scoped.

## Summary

| Environment | Config File | Location | Install |
|---|---|---|---|
| claude.ai | Memory edits | Automatic | Already done |
| Claude Code CLI | CLAUDE.md | Project root | Copy file |
| Claude Code Plugin | plugin/ folder | ~/.claude/plugins/ | Copy folder |
| Cowork | Global Instructions | Settings → Cowork | Paste text |
| Cowork | memory.md | Working folder | Copy file |
