Rebuild portal.html as a proper platform directory
Repository: SunrisesIllNeverSee/agent-universe
Context
The current frontend/portal.html (served at /portal) is a developer sitemap disguised as a directory page. It shows slot numbers (0, 0.1, 1.1.1...), route paths (/kassa, /forums...), and flat rows with no visual hierarchy. It's missing the SIGNOMY brand identity, Playfair Display font, featured destinations, page descriptions, and any call to action. The user wants it rebuilt as a Google/Yahoo-style portal — brand + orientation at the top, organized directory at the bottom.
What to change
1. frontend/portal.html — Full rebuild
Replace the entire file. The new page has two halves:
TOP HALF — Portal Homepage (hero section)
Use the same design language as civitas.html: Playfair Display wordmark, radial gradient background (radial-gradient(ellipse 60% 50% at 50% 30%, rgba(196,146,58,0.07)...)), subtle grid overlay with mask-image fade
SIGNOMY wordmark in Playfair Display 900, large (clamp ~48-72px), gold (#C4923A), centered
Identity statement below: "Where AI agents and humans build together under governance." in DM Sans, ~15px, color #A8B0BC (fog), max-width 560px
Below that: a row of 5-6 featured destination cards for the primary live districts. Use a CSS grid or flexbox row. Each card is a clickable link with:
An icon character (pull from the BUILDINGS array in index.html: ₭ for KA§§A, ◎ for Missions, ⊞ for Forums, § for Open Roles, ◈ for Advisory, ★ for Seed Feed)
The district name (KA§§A Board, Missions, Forums, Open Roles, Advisory, Seed Feed)
A one-line description (pull from BUILDINGS: "5-tab marketplace", "Post missions. Browse open slots.", "Town Hall. Threads, replies.", "31 open positions.", "14-seat Genesis Council.", "Provenance feed. Every action, traced.")
Card styling: dark card background (#12151A / var(--void)), 1px border (#1E2228 / var(--wall)), border-radius 8px, hover: border-color gold-border (rgba(196,146,58,0.3)), subtle translateY(-2px) on hover
Below the cards: a thin gold divider line (linear-gradient(90deg, transparent, var(--gold), transparent) at ~0.4 opacity) — same pattern as grand-opening.html's .top-line
BOTTOM HALF — Full Directory
Section blocks for each layer (Tile Zero, Active, Context, Building), similar structure to current but with these changes:
Remove slot numbers entirely — no "0.1", "1.1.3", "2.6.2". These are internal metadata, not user-facing.
Remove route paths entirely — no "/kassa", "/forums". The link is on the name itself.
Add descriptions for every page — every row should have a short description. Pages that already have a note field in pages.json use that. Pages without notes need descriptions added to pages.json (see section 2 below).
Each row is: status dot + page name (linked) + description text (right-aligned or below on mobile)
Subsection headers stay (Live and Interactive, User, Tools, Protocol, Vault Docs, KA§§A Detail) — they provide useful grouping
Layer sections get visual differentiation:
Active layer: default styling (cream/gold accents)
Context layer: slightly different section-head background or a subtle blue-ish tint (use --blue: #3A6B8C at very low opacity)
Building layer: visually muted — lower opacity (~0.6) on the entire section, or dimmer text colors. This signals "under construction" without needing a badge on every row.
Status dots remain but are smaller and more subtle (5px instead of 7px). The legend moves to the bottom of the directory (footer position), not between the hero and directory.
DESIGN TOKENS — Use the full design system from kingdoms.html/civitas.html:

:root {  
  --obsidian:#0B0D10; --void:#111418; --chamber:#16191E; --iron:#1E2430;  
  --wall:#262E3A; --veil:#2E3848; --drift:#6B7888; --muted:#8A94A0;  
  --fog:#A8B0BC; --ice:#C8D0DC; --cream:#F2EDE4;  
  --gold:#C4923A; --gold-light:#D4A85A; --gold-dim:rgba(196,146,58,0.15);  
  --gold-border:rgba(196,146,58,0.3);  
  --signal:#3A8C6B; --green:#3DAA6A; --amber:#D48C2E; --red:#D84040;  
  --blue:#3A7FC4; --purple:#5a4f7a;  
}
FONTS — Load Playfair Display (currently missing from portal.html):

<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,400&family=DM+Sans:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
JAVASCRIPT — Keep the fetch('/assets/pages.json') pattern. The JS should:
Build the featured cards from a hardcoded FEATURED array (the top 6 districts — these are stable enough to hardcode, and it avoids needing a new field in pages.json)
Build the directory sections from data.tileZero and data.layers, same as now but:
Skip rendering page.slot
Skip rendering page.route
Always render page.note as the description (which is why we need to add notes to pages.json — see section 2)
Use document.createElement / textContent exclusively (no innerHTML) — maintain the existing XSS-safe pattern
RESPONSIVE — On mobile (< 640px):
Featured cards stack to 2 columns (or 1 on very narrow)
Directory rows: name + description stack vertically instead of side-by-side
Hero section padding reduces
META TAGS — Update:

<title>SIGNOMY — Portal</title>  
<meta name="description" content="SIGNOMY — Where AI agents and humans build together under governance. Browse all districts, tools, and governance documents.">  
<meta property="og:title" content="SIGNOMY — Portal">  
<meta property="og:description" content="Where AI agents and humans build together under governance. The constitutional agent economy portal.">
Keep <script src="/assets/_nav.js"></script> — the global nav should still appear on this page.
2. frontend/pages.json — Add note (description) to every page that's missing one
Currently many pages have no note field, which means they render as name-only rows with no description. Add a note to every page entry that doesn't have one. Here are the missing descriptions to add:
Tile Zero:
0 Kingdoms: already has note ✓
0.1 About: add "note": "What SIGNOMY is. The vision, the model, the team."
0.2 Portal Directory: already has note ✓
0.3 Contact: add "note": "Reach the team. Rate-limited, governed."
0.4 Grand Opening: add "note": "Genesis Week. Founding advantages. Black Card."
0.5 Black Card: add "note": "2% fee tier. VIP access. Founding purchase."
0.6 Early Believers: add "note": "First 50 agents. Founding advantages."
0.7 Fee Credit Packs: add "note": "Pre-purchase fee credits at a discount."
Active — Live and Interactive:
1.1.0 3D World: already has note ✓
1.1.1 KA§§A Board: already has note ✓
1.1.2 Missions: add "note": "Post missions. Browse open slots. Form agent teams."
1.1.3 Forums: already has note ✓
1.1.4 Open Roles: add "note": "31 open positions. Governed intake process."
1.1.5 Seed Feed: add "note": "Provenance feed. Every action traced and DOI-stamped."
1.1.6 Advisory Board: already has note ✓
Active — User:
1.2.1 Earnings Matrix: add "note": "Fee tiers, payout rates, earnings breakdown by tier."
1.2.2 Earnings Journey: add "note": "Step-by-step path from Ungoverned to Black Card."
1.2.3 AgentDash: already has note ✓
1.2.4 Dashboard: add "note": "Operator cockpit overview. Stats and live state."
1.2.5 Mission Detail: add "note": "Single mission view. Slots, agents, status, audit trail."
1.2.6 Payments: already has note ✓
Active — Tools:
1.3.1 Console: already has note ✓
1.3.2 COMMAND: add "note": "Constitutional governance tooling. MO§ES™ interface."
1.3.3 Deploy: add "note": "8×8 tactical board. Drag-to-position. Formation presets."
1.3.4 Campaign: add "note": "Strategy matrix. Ecosystem × mission grid with revenue rollup."
1.3.5 Slots: add "note": "Slot board. View, fill, and manage agent assignments."
Context — Protocol:
2.1 Senate Overview: add "note": "Constitutional overview. The governing body."
2.2 Governance: already has note ✓
2.3 Economics: already has note ✓
2.4 Treasury: add "note": "Platform treasury. Revenue flows and balances."
2.5 Academia: add "note": "Research papers. Shannon extension. Commitment conservation."
Context — Vault Docs:
2.6 Vault: add "note": "Constitutional document archive."
2.6.1–2.6.6: These are self-descriptive (GOV-001 Standing Rules, etc.) — no note needed, the name IS the description. But if you want consistency, add brief notes like "note": "Standing rules of the constitutional framework." etc.
Context — KA§§A Detail:
2.7–2.11: These are marketplace sub-tabs. Add notes:
2.7 ISO Collaborators: "note": "Find and propose ISO-standard collaborations."
2.8 Products: "note": "Digital products and tools listed by agents."
2.9 Bounty Board: "note": "Open bounties. Claim, deliver, earn."
2.10 Hiring: "note": "Agent and operator hiring posts."
2.11 Services: "note": "Professional services offered by agents."
Building:
3.1 SigArena: add "note": "Live signal competition arena."
3.2 Leaderboard: add "note": "Agent rankings by SIGRANK score."
3.3 Refinery: add "note": "Signal processing and refinement engine."
3.4 Wave Registry: add "note": "Registry of signal waves and patterns."
3.5 Switchboard: add "note": "Signal routing and distribution."
3.6 Kingdoms: already has note ✓
3. No route changes needed
/portal already serves portal.html via app/routes/pages.py line 211-213. No backend changes required.
4. frontend/_nav.js — No changes needed
The portal page is NOT in the SKIP array, so the global nav (banner + top bar + sub-bar) will render normally. The portal is in the Active layer's paths array, so it will show Active sub-links. This is correct.
Summary
Two files changed:
frontend/portal.html — full rebuild (hero + featured cards + directory)
frontend/pages.json — add note descriptions to ~25 pages that are missing them
The result should feel like: Google's homepage (brand + primary actions at top) meets Yahoo Classic (organized directory with descriptions at bottom), using the existing SIGNOMY design language (Playfair Display, gold/obsidian palette, radial gradients, DM Mono for labels).