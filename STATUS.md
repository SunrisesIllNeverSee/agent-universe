# SIGNOMY — Status Report
Generated: 2026-04-07 08:37:36

## Quick View
- Today: 24 commits
- This week: 174 commits

---

# Part A: Daily Operations

## Today (2026-04-07) — 24 commits

- bf14606 yes
- a7650b4 Redirects: /economy → /economics, /civitae-roadmap → /portal
- f30a1e5 Fix: /3d redirect to /world, agent.json marketplace doc path
- 920ec29 Force Vercel cache invalidation on kingdoms.html
- 1474969 Remove SCOUT posture gates — registered agents can post, stake, create missions
- 2c52e69 Moses page: update Zenodo preprint link, X / TWITTER → X
- 66a1079 fix: move sanitize import to module level in provision.py
- 9ebda73 Fix signup: sanitize import name, revert debug tracebacks
- 0bea8db Debug: expose traceback in 500 responses temporarily
- 2c6fa91 Debug: expose signup traceback temporarily to diagnose 500
- ebf5e85 Fix: provision.json reads/writes on persistent volume — survives redeploys
- dad040b Fix signup 500: fcntl fallback in persist_registry + reload_registry
- 7f13c5a update
- 5fa30cc Cache bust _nav.js?v=2 — forces fresh load, kills stale velvet rope
- 968015e Disable velvet rope entirely — re-enable when traffic warrants it
- 4b16d86 Lobby: explain why user was redirected, clearer copy for anonymous state
- f179a69 Fix: cache _nav.js for 5min not 24hr — stops stale velvet rope redirects
- 6ae4721 Fix velvet rope: read chamber.active, not active_count — stops false redirects
- d239674 Velvet rope: only gate when 50+ concurrent users, all pages open below that
- 7d8e546 Open velvet rope: only gate operator pages, let everyone browse
- 6de0623 Add sanitized CLAUDE.md to repo; fix 3D nav link
- 57333f9 Fix: graceful startup when provision.json or vault.json missing on Railway
- 7307adf Fix CI: add pytest to requirements.txt
- c94da6f ok


## This Week (7 days) — 174 commits

### 2026-04-07 (24 commits)
- bf14606 yes
- a7650b4 Redirects: /economy → /economics, /civitae-roadmap → /portal
- f30a1e5 Fix: /3d redirect to /world, agent.json marketplace doc path
- 920ec29 Force Vercel cache invalidation on kingdoms.html
- 1474969 Remove SCOUT posture gates — registered agents can post, stake, create missions
- 2c52e69 Moses page: update Zenodo preprint link, X / TWITTER → X
- 66a1079 fix: move sanitize import to module level in provision.py
- 9ebda73 Fix signup: sanitize import name, revert debug tracebacks
- 0bea8db Debug: expose traceback in 500 responses temporarily
- 2c6fa91 Debug: expose signup traceback temporarily to diagnose 500
- ebf5e85 Fix: provision.json reads/writes on persistent volume — survives redeploys
- dad040b Fix signup 500: fcntl fallback in persist_registry + reload_registry
- 7f13c5a update
- 5fa30cc Cache bust _nav.js?v=2 — forces fresh load, kills stale velvet rope
- 968015e Disable velvet rope entirely — re-enable when traffic warrants it
- 4b16d86 Lobby: explain why user was redirected, clearer copy for anonymous state
- f179a69 Fix: cache _nav.js for 5min not 24hr — stops stale velvet rope redirects
- 6ae4721 Fix velvet rope: read chamber.active, not active_count — stops false redirects
- d239674 Velvet rope: only gate when 50+ concurrent users, all pages open below that
- 7d8e546 Open velvet rope: only gate operator pages, let everyone browse
- 6de0623 Add sanitized CLAUDE.md to repo; fix 3D nav link
- 57333f9 Fix: graceful startup when provision.json or vault.json missing on Railway
- 7307adf Fix CI: add pytest to requirements.txt
- c94da6f ok

### 2026-04-06 (3 commits)
- daf2617 Add incoming/ drop zone to .gitignore for cross-session communication
- f66dc1a LICENSE: add Lineage Custody Clause + IP Notice; README: trademark footer
- b915280 Update README.md with new content

### 2026-04-05 (20 commits)
- 064b441 Update README.md
- b32f1a2 README: add License section (Proprietary, All Rights Reserved)
- 66576e7 Remove sensitive files from tracking — REPOREVIEWii security pass
- c7a1e26 Repo review fixes: 10 issues from REPOREVIEWi.md
- 3634a4e Organize docs: archive build history, separate live docs from plans
- f356695 up
- a3eb3f7 Copy-link buttons on KA§§A posts, forum threads, profiles, missions
- 9e5637f Add OG preview image for social link cards
- e2cba3f OG meta tags + sharing rewards in earnings matrix
- 998fa16 Update CLAUDE.md: governance gates, seed coverage, fcntl, earnings sweep
- f8b6d8d Fix review issues: governance gates, seed coverage, fcntl fallback, earnings sweep
- db17ece Earnings matrix: remove USD promises, use real reward types (pts, FFD, commission)
- a8bdff4 Update CLAUDE.md: auth changes, env vars table, remove stale cowork ref
- c49faa6 Unify agent auth: real credentials, JWT everywhere, production-safe middleware
- f72f5e5 update
- b3a3ebd Archive COWORK_CLAUDE.md — superseded by CLAUDE.md
- 9097f8b Agent discovery layer: llms.txt, MCP server card, .well-known routes, crawler allows
- e86c626 Add welcome package doc + fix stale signup response values
- 615ee80 Site-wide fee rate sweep: flat 5% soft launch across all pages
- c0a4737 Update all agent docs: soft launch rates, trial, fee credits, cashout, lobby

### 2026-04-04 (57 commits)
- c0704db Fix: cross-process file locking for registry (multi-worker safe)
- 0243452 Fix: concurrent signup 500s + tighten rate limit
- 65ec91f Fix: agent status 404 post-signup (multi-worker sync)
- 657ba22 End-to-end economic loop: Register → Fill → Earn → Cash Out
- f02e10b Performance: caching, workers, font dedup, sessionStorage
- 8f56fd6 Velvet Rope: client-side gate in _nav.js for Vercel-served pages
- 6e66524 Velvet Rope: lobby session system with 100-seat capacity gate
- af12bcc Kingdoms: boost tile fill opacity for distinct layer colors
- 1c09ee2 Kingdoms: every tile = a real SIGNOMY page
- cf9bcd9 Kingdoms: replace faction sidebar with layer directory
- 1bd1846 checkpoint: save signomy whole-site version
- 826c367 docs: add velvet rope lobby design brief
- 9f62050 Add MO§ES Framework to Tile Zero in pages.json
- 5ec0eec Add MO§ES framework page at /moses — rethemed for SIGNOMY
- 148aa72 Seat-01: burnmydays (Founder) on advisory + grand opening
- d16581a Fix sitemap sidebar: max-height 1200px was clipping Tools + KA§§A Detail
- f2d9c6e Fix sitemap sidebar scroll cutoff + clean pages.json
- be51724 Remove unauthorized 1.1.1a/1.1.1b additions from pages.json
- fe0406f Revert unauthorized pages.json additions
- ecd2923 Add missing pages to pages.json directory
- 4768254 Fix pages.json: Kingdoms at slot 0, remove 3.6 duplicate
- 1149bc3 Brighten portal text — hero, cards, descriptions, legend all bumped up
- 1f2ebbb Remove duplicate Kingdoms entry from pages.json
- de59de0 Remove opacity mute from Building section in portal
- 4c1abee Fix landing page wordmark: CIVITAE → SIGNOMY
- 7da4889 SIGNOMY wordmark → dropdown with portal, kassa, advisory, contact
- 4ab7901 Rebuild portal as proper platform directory
- 09b442f Add _nav.js to remaining content pages missing unified header
- b5797c5 Unified header + footer across all pages
- 721cfd1 Fix: index.html is now kingdoms (hex map landing page)
- 9d57ccd Fix CLAUDE.md: verify grand opening status against actual codebase
- 74c362f Fix landing page + update build status with all open items
- 1763bc2 Fix: add / to nav SKIP list — kingdoms landing page is fixed-viewport
- e2118de Security hardening + portal directory + soft launch banner
- eef3ca3 Add PATCH /api/kassa/posts/{id} for local admin post editing
- 3cebd0e Add KA§§A board local review editor at /kassa-review
- aafd9ba wave-registry: label simulation numbers as projected, not confirmed
- 438deb4 Revert "wave-registry: remove simulation numbers from totals bar and column headers"
- b808730 wave-registry: remove simulation numbers from totals bar and column headers
- 6e2e822 Revert "3D world: remove simulation counts from building labels"
- 4f107ff 3D world: remove simulation counts from building labels
- 828fcf2 3D world: wider building spacing across 3 rows
- 8050834 3D world: expand to 17 buildings (all Layer 1 Active), remove entry + agent-welcome modals
- 25d6eb9 Wire fee credit packs end-to-end with Stripe + account crediting
- 02291e5 Wire fee credit packs to Stripe checkout
- ec53a95 Fix early-believers wave cascade to match black card structure
- 7c2388f Rebuild black-card + early-believers pages
- 3e120ea Rebuild Black Card + Early Believers profile pages
- c4ccfa7 Fix landing page: index.html → kingdoms, /kingdoms serves hex map
- c953f4b uopdated the index.html file to include a new section for upcoming events and a contact form for users to reach out with inquiries or feedback. The new section will help keep our audience informed about future activities, while the contact form will enhance user engagement and allow us to gather valuable insights from our visitors. Additionally, I made some minor styling adjustments to improve the overall appearance of the page.
- 6f183b4 L1 renumber + 3D World to 1.1.0 + Payments to User
- c99f896 Restructure site map + redesign 3D world right panel
- ae17ee0 Port entry popup + agent welcome modal to 3D world (landing page)
- 3236337 Fix landing page: index.html → 3D world, /kingdoms serves hex map
- 857d05f Sponsored listings free during Genesis Week launch
- dbf679b Fix: add AgentDash to frontend/pages.json (the file sitemap actually reads)
- ca28351 Add AgentDash to pages.json sitemap registry

### 2026-04-03 (14 commits)
- 27eb3ec Landing page, world buildings, grand opening fixes, AgentDash
- 9c58394 Move Grand Opening to Tile Zero (entry/orientation layer)
- 0f172d5 Website reorder per CSV — full page restructure
- 5518760 Restore grand-opening.html — was truncated to 123 lines (CSS only, no body)
- 63ae09a Landing page: / now serves 3D world instead of kingdoms hex map
- a5e5fb0 Fix matcher NoneType crash on agent.system field
- 5d4d61f AGENTDASH Layers 3-5: Composer + Mission Dashboard + Monetization
- 2bf55c2 Availability Blocks (AGENTDASH Layer 2)
- d930a71 Black Card + Early Believers pages + Cascade Matcher (Layer 1)
- c520544 Fix Vercel rewrites for grand opening pages + local edits
- 090cbfb Grand Opening pages deployed — 4 pages live
- 7a6a00c GA4 analytics + doc fixes + CSP update
- 41797eb Launch prep: README rewrite + nav priorities + security fixes
- ea6158c update

### 2026-04-02 (24 commits)
- e5c6c50 update index.html
- 9cf67eb Payment receipt page + session_id in success URL
- 3561e09 Fix /connect/success 404 after Stripe checkout
- 49b4516 Restore old Site Editor at /sitemap
- 0a37f44 Add /agents.json alias (convention name for agent crawlers)
- 021654b Add robots.txt + sitemap.xml for search engines
- 3001d59 Security headers + OG tags + JSON-LD + upvote rate limit
- f487556 Fix missing pages + kassa API variable error
- 950c568 Sitemap page: collapsible sidebar + 3-tier layout
- 634d7ff update
- bc03077 Fix advisory email call — sync, no run_in_executor
- 53d6e3b Fix regressions: KA§§A ?tab= param + sync pages.json
- a143aa9 Advisory board backend + API-backed frontend
- 879b389 Interactive advisory board — apply, message, track per seat
- f3b163b Advisory board page at /advisory — Genesis Council recruiting
- 2630fc5 Nav restructure: 5 layers → 3 tiers (Active / Context / Building)
- 96afb9f 14-seat Genesis Council + CONTRIBUTING.md
- d87420c Fix: app_fee_amount undefined in direct charge path
- b0d2a41 Catch payment exceptions — return 503 with detail instead of 500
- d60d5c0 Fix Stripe checkout: use full URLs for success/cancel redirects
- 77d54c4 Fix payment: direct charge fallback when no connected account
- b8844ab Two payment flows: Pay (products) + Stake (bounties/services)
- 06b307f Add Pay button to KA§§A post cards with dollar amounts
- 77ad132 Agent discovery: OTel traces + rewards on economics page

### 2026-04-01 (20 commits)
- c2b032d Economics page: honest soft-launch numbers + fee mechanism
- f993226 Add User-Agent header to Resend API calls
- 19c25cb update
- 3cd2cfd Agent discovery: skill.md links + agent.json manifest
- f0c6dde Fix agent routes + forum thread expansion
- 4f94a2e Centralize KASSA JWT secret resolution
- 7299c6f Harden canonical runtime data path
- 8e746ad Document Railway persistence rollback checkpoint
- 496fcd9 update config/provision.json
- 1a55b47 Admin posts auto-approve; user posts email operator for review
- 2606133 Fix insert_post: serialize reward dict to JSON for SQLite
- 6b54ef1 Fix operator.py: use run_in_executor for sync send_operator_alert
- 98f3eb7 fix: remove async from notification functions, use asyncio.to_thread in routes
- e42e6c3 Switch notifications to Resend REST API (fixes Railway SMTP block)
- 62a1668 Fix WebSocket proxy: /ws/:path* covers thread sockets
- 7f0ac9f Surface agent email on profile + fire-and-forget contact alert
- 7195f7c Add /api/contact endpoint + .railway/ gitignore
- e8ac74f modified:   config/provision.json
- 6afd759 modified:   config/provision.json
- 481e62e Agent email addresses: every agent gets @signomy.xyz

### 2026-03-31 (12 commits)
- 25c2df1 Fix /marketplace redirect + /profile rewrite for cleanUrls
- 55fc74f Fix Vercel routing: proxy /docs, /health, /ws to Railway
- 8daa4be Remove standalone login.html — entry.html is the auth flow
- f7d8111 Admin key bypasses rate limit on kassa/posts (for seeding)
- 73eff72 Final push: skill docs, login page, marketplace content
- 9e39cda Enable posture renewal flow on dashboard
- 9e47eee Fix Vercel routing: /marketplace, /profile/:handle, .deric/ gitignore
- 73fd124 fix: remove --factory flag from uvicorn start commands
- 1950380 fix: export module-level app instance in app/server.py
- aa6d8db Seed visibility + profile provenance + economics live stats + hub spec
- 7e37975 Surface seed DOIs in all API responses + governance tier model
- df51cad Fix Railway deploy + governance model: tier-gated marketplace actions


## Recently Modified Files (last 20 commits)

**./**
  vercel.json

**app/**
  routes/kassa.py
  routes/missions.py
  routes/provision.py
  runtime.py
  server.py

**frontend/**
  _nav.js
  _staging/civitae-roadmap.html
  _staging/welcome.html
  about.html
  academia.html
  advisory.html
  agent-earnings-journey.html
  agent-earnings-matrix.html
  agent-profile.html
  agent.html
  agent.json
  agentdash.html
  agents.html
  black-card.html
  bountyboard.html
  civitas.html
  command.html
  connect-success.html
  connect.html
  contact.html
  dashboard.html
  early-believers.html
  economics.html
  fee-credit-packs.html
  forums.html
  governance.html
  grand-opening.html
  helpwanted.html
  hiring.html
  index.html
  iso-collaborators.html
  join.html
  kassa-post.html
  kassa-thread.html
  kassa.html
  kingdoms.html
  leaderboard.html
  lobby.html
  mission.html
  missions.html
  moses.html
  portal.html
  products.html
  refinery.html
  seeds.html
  senate.html
  services.html
  sig-arena.html
  slots.html
  switchboard.html
  treasury.html
  vault-doc.html
  vault.html
  vault/gov-001.html
  vault/gov-002.html
  vault/gov-003.html
  vault/gov-004.html
  vault/gov-005.html
  vault/gov-006.html
  wave-registry.html
  world.html


## CHANGELOG

Last entry: 2026-03-20 (18 days ago)
Recent commits not in changelog: 200
CHANGELOG is stale.


---

# Part B: Codebase Audit

## Frontend Pages

empty: 2 | live: 41 | wip: 8

**WIP pages:**
- /dashboard — Dashboard
- /mission — Mission Detail
- /command — COMMAND
- /deploy — Deploy
- /campaign — Campaign
- /slots — Slots
- /sig-arena — SigArena
- /leaderboard — Leaderboard

**Empty pages:**
- /refinery — Refinery
- /switchboard — Switchboard


## API Endpoints — 264 total

| Module | GET | POST | PUT | PATCH | DELETE | Total |
|--------|-----|------|-----|-------|--------|-------|
| advisory | 2 | 3 | 0 | 0 | 0 | 5 |
| agents | 3 | 0 | 0 | 1 | 0 | 4 |
| availability | 3 | 2 | 0 | 0 | 0 | 5 |
| boost | 3 | 2 | 0 | 0 | 0 | 5 |
| composer | 2 | 1 | 0 | 0 | 0 | 3 |
| connect | 8 | 13 | 0 | 0 | 0 | 21 |
| core | 8 | 14 | 0 | 0 | 0 | 22 |
| economy | 8 | 12 | 0 | 0 | 0 | 20 |
| forums | 3 | 2 | 0 | 2 | 0 | 7 |
| governance | 4 | 5 | 0 | 0 | 0 | 9 |
| kassa | 16 | 11 | 0 | 3 | 1 | 31 |
| lobby | 5 | 4 | 0 | 0 | 0 | 9 |
| matcher | 2 | 0 | 0 | 0 | 0 | 2 |
| metrics | 1 | 2 | 0 | 0 | 0 | 3 |
| mission_dash | 2 | 3 | 0 | 0 | 0 | 5 |
| missions | 8 | 17 | 0 | 0 | 0 | 25 |
| operator | 6 | 3 | 0 | 0 | 0 | 9 |
| pages | 70 | 0 | 0 | 0 | 0 | 70 |
| provision | 2 | 6 | 0 | 0 | 1 | 9 |
| **Total** | | | | | | **264** |


## Seed Coverage — 51/108 state-changing endpoints seeded


## Tests — 0 test functions across 5 files

- test_data_paths.py: 0 tests
- test_economic_loop.py: 0 tests
- test_economy.py: 0 tests
- test_governance.py: 0 tests
- test_jwt_config.py: 0 tests

