# Theme System & Skin Swap
## COMMAND · powered by MO§ES™
**Ello Cello LLC · Technical Reference · Internal**
*March 2026 — Do when ready, not urgent*

---

## CURRENT STRUCTURE — WHY IT'S ALREADY BUILT FOR THIS

The codebase uses a centralized CSS variable system in `:root` starting at line 46. Every color reference throughout the file uses `var(--token)` — not hardcoded values. This is the professional design system approach and means a full theme swap requires zero structural changes.

**Current dark theme tokens:**

```css
:root {
  --void: #050507;
  --deep: #0a0a0f;
  --surface: #0f0f18;
  --panel: #13131e;
  --border: #1e1e2e;
  --accent: #c8a96e;
  --accent2: #6e9ec8;
  --signal: #7ec86e;
  --warn: #c86e6e;
  --text: #d4d4e8;
  --muted: #5a5a7a;
  --mono: 'Share Tech Mono', monospace;
  --display: 'Syne', sans-serif;
  --body: 'DM Sans', sans-serif;
}
```

**Hardcoded exceptions (minor):**
- `#c8c4b4` — topbar/footer text
- `#ffffff` — sparse high-contrast labels
- Some `rgba()` opacity variants of accent colors

These are not scattered — they're contextual. Easy to clean up when the time comes.

---

## THE CLEAN ENTERPRISE THEME — READY TO DROP IN

Add this block to the CSS. No other changes needed. The entire UI flips.

```css
[data-theme="clean"] {
  --void: #ffffff;
  --deep: #f7f8fa;
  --surface: #eef0f3;
  --panel: #ffffff;
  --border: #d1d5db;
  --accent: #3b82f6;
  --accent2: #10b981;
  --signal: #10b981;
  --warn: #ef4444;
  --text: #111827;
  --muted: #6b7280;
  --mono: 'IBM Plex Mono', monospace;
  --display: 'Inter', sans-serif;
  --body: 'Inter', sans-serif;
}
```

Apply to the body tag: `<body data-theme="clean">`  
Toggle back to dark: `<body data-theme="dark">` or remove attribute entirely.

---

## EXECUTION PLAN — ONE DAY WHEN READY

**Step 1 — Add the clean theme block**
Paste the `[data-theme="clean"]` block directly below the existing `:root` block. No other CSS changes.

**Step 2 — Fix hardcoded exceptions**
Find/replace `#c8c4b4` → add as `--neutral-light` in both theme blocks.  
Find/replace `#ffffff` → add as `--pure-white` in both theme blocks.  
Check for any remaining `rgba()` hardcodes and convert to variable-based equivalents.

**Step 3 — Add toggle (optional)**
Simple JS one-liner:
```javascript
document.body.setAttribute('data-theme', 
  document.body.getAttribute('data-theme') === 'clean' ? 'dark' : 'clean'
);
```
Wire to a button. Can store preference in `localStorage` if persistence is needed.

**Step 4 — Test all states**
Modals, tabs, hover states, locked/open seat cards, admin panel, all form inputs. Screenshot both versions side by side.

---

## FUTURE-PROOFING (IF DESIRED)

Move all hardcoded colors into `:root` as named variables: `--neutral-light`, `--pure-white`. From that point, any new theme is just a new `[data-theme="x"]` block — no hunting through the file for exceptions.

PostCSS or Sass would enable compiled theme variants if the project ever scales to multiple deployments. Not needed now.

---

## DEPLOYMENT PLAN

- **mos2es.io** — stays dark. This is the product, the identity, the demo of what's possible.
- **Replit** — clean enterprise theme. Linked from mos2es.io. Demo URL for white-label conversations and enterprise prospects.
- **The toggle** — exists in the Replit version to show the swap live. This *is* the white-label pitch: one click, full rebrand.

---

## CONTEXT

This work is not urgent. The codebase is ready whenever the clean version is needed.  
The customization scope (colors, typography, labels) is already documented in `Customization_Scope.md`.  
The full component and function list remains internal — disclosed at transfer, not before.

---

*COMMAND · powered by MO§ES™*
*© 2026 Ello Cello LLC · All Rights Reserved · Technical Reference*
