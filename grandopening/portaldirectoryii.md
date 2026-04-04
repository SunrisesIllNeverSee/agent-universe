The cleanest approach: a **data-driven global banner injected via `_nav.js`**, controlled by a single field in `pages.json`. One line to add, one line to remove when you're ready.

Here's why this is the right pattern for this project:

**1. `_nav.js` already injects on every content page** — it builds the top bar and sub-bar dynamically from `pages.json`. Adding a banner row is one more `createElement` call in the same injection flow. [12-cite-0](#12-cite-0) 

**2. `pages.json` already drives the nav** — adding a `"siteBanner"` field keeps the pattern consistent. When you want to kill the banner, delete the field. No code change, just data. [12-cite-1](#12-cite-1) 

**3. The SKIP pages (console, deploy, campaign, kingdoms) have their own topbars** — those would need their own banner or skip it. Given that console is an operator tool and kingdoms is the landing page, you probably want the banner there too. But that's a separate decision. [12-cite-2](#12-cite-2) 

**On tone** — the Grand Opening spec already nailed it: "Credibility is the product." The disclaimer shouldn't be apologetic ("sorry, under construction") or generic ("beta"). It should be structural and honest, matching the voice of the rest of the site.

Something like:

> **Live platform · Active development** — Some districts are still being built. Governance is running. The audit log is recording.

Or shorter:

> **Soft launch** — The platform is live and functional. Some pages are still under construction.

Or in the project's own voice:

> **The doors are open. The build continues.** Some districts are live. Others are coming online.

The existing "Coming Soon" badge on `sig-arena.html` already has the right visual pattern — a pulsing dot + mono text in a bordered pill: [12-cite-3](#12-cite-3) 

The global banner would be a thinner version of that: a 28-32px bar with a pulsing amber dot, DM Mono text, gold-dim background, sitting above the nav or between the nav and content.

```
┌──────────────────────────────────────────────────────────────┐
│  ● SOFT LAUNCH — Live platform. Active development.          │  ← 28px banner
├──────────────────────────────────────────────────────────────┤
│  SIG NOMY                    Active | Context | Building     │  ← 64px top bar
├──────────────────────────────────────────────────────────────┤
│  KA§§A   Advisory   Forums   Missions   Open Roles           │  ← 36px sub-bar
├──────────────────────────────────────────────────────────────┤
│                         page content                         │
```