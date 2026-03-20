# Changelog

All notable changes to the MO§E§™ Governance plugin will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioned per [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-07

### Added
- 9 slash commands: /govern, /posture, /role, /vault, /command, /audit, /hash, /status, /docs
- 6 auto-activating skills: governance-mode, posture-control, role-hierarchy, audit-trail, context-assembly, doc-numbering
- 3 agent definitions: Primary, Secondary, Observer
- 2 Python scripts: governance.py (mode translation + context assembly), audit.py (SHA-256 hash chain)
- 4 context files: high-security, research, creative, defense
- 1 rules file: constitutional governance rules (always-follow)
- Hooks: PreToolUse governance check, PostToolUse audit logging, SessionStart announcement
- 4 worked examples: treasury governance, code review, research pipeline, multi-agent coordination
- Documentation: Quickstart, Architecture, Enterprise Use, Patent Notice
- settings.json with safe defaults (Unrestricted mode + SCOUT posture)
- marketplace.json for plugin discovery
- Full patent and license documentation

### Notes
- Patent pending: PPA4, Serial No. 63/877,177
- Peer-reviewed paper published with independent validation
- Live demo at mos2es.io
