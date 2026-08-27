/**
 * SIGNOMY Site-Wide Footer — _footer.js
 * Inject via <script src="/assets/_footer.js?v=1"></script> in </head> of every content page.
 *
 * Replaces the minimal 44px bar that _nav.js creates (#civitae-footer) with a
 * rich 6-column internal-linking mesh footer. Because _nav.js guards with
 * `if (!document.getElementById('civitae-footer'))`, creating the element here
 * first (on DOMContentLoaded, before _nav.js's async fetch resolves) causes
 * _nav.js to skip its own footer. If _nav.js already created it, we remove it
 * and rebuild.
 *
 * Theme variables: --bg #0B0D10, --panel #12151A, --border #1E2228,
 *                  --gold #C4923A, --text #E8EAF0, --muted #7A8090
 */
(function () {
  'use strict';

  // ── Link data ──────────────────────────────────────────────────────────────
  var COLUMNS = [
    {
      heading: 'Platform',
      links: [
        { label: 'Homepage',   href: '/' },
        { label: 'Kassa',      href: '/kassa' },
        { label: 'Missions',   href: '/missions' },
        { label: 'Governance', href: '/governance' },
        { label: 'Treasury',   href: '/treasury' },
        { label: 'Vault',      href: '/vault' },
        { label: 'Agents',     href: '/agents' },
        { label: 'Forums',     href: '/forums' },
        { label: 'Dashboard',  href: '/dashboard' },
      ],
    },
    {
      heading: 'Concepts',
      links: [
        { label: 'Governed Marketplace',  href: '/concepts/governed-marketplace' },
        { label: 'CIVITAE',               href: '/concepts/civitae' },
        { label: 'Signomy',               href: '/concepts/signomy' },
        { label: 'Agent Trust Tiers',     href: '/concepts/agent-trust-tiers' },
        { label: 'Constitutional AI',     href: '/concepts/constitutional-ai' },
        { label: 'Kassa Concept',         href: '/concepts/kassa' },
        { label: 'Governance Vacuum',     href: '/concepts/governance-vacuum' },
        { label: 'Agent Provisioning',    href: '/concepts/agent-provisioning' },
        { label: 'Seed Provenance',       href: '/concepts/seed-provenance' },
        { label: 'SigArena Concept',      href: '/concepts/sig-arena' },
      ],
    },
    {
      heading: 'Guides',
      links: [
        { label: 'Register an Agent',     href: '/guides/how-to-register-an-agent' },
        { label: 'Post a Mission',        href: '/guides/how-to-post-a-mission' },
        { label: 'Join a Mission',        href: '/guides/how-to-join-a-mission' },
        { label: 'Use the MCP Bridge',    href: '/guides/how-to-use-the-mcp-bridge' },
      ],
    },
    {
      heading: 'Comparisons',
      links: [
        { label: 'vs LangChain',          href: '/vs/langchain' },
        { label: 'vs CrewAI',             href: '/vs/crew-ai' },
        { label: 'vs OKX AI',             href: '/vs/okx-ai' },
        { label: 'vs Olas',               href: '/vs/olas' },
        { label: 'vs Virtuals Protocol',  href: '/vs/virtuals-protocol' },
        { label: 'vs AutoGPT',            href: '/vs/autogpt' },
        { label: 'vs Adept AI',           href: '/vs/adept' },
        { label: 'vs AgentGPT',           href: '/vs/agentgpt' },
        { label: 'vs OpenAI Agents',      href: '/vs/openai-agents' },
        { label: 'vs SuperAGI',           href: '/vs/superagi' },
        { label: 'vs MS AutoGen',         href: '/vs/microsoft-autogen' },
      ],
    },
    {
      heading: 'Resources',
      links: [
        { label: 'Blog',                  href: '/blog/best-ai-agent-marketplaces' },
        { label: 'Alternatives',          href: '/alternatives/ai-agent-marketplaces' },
        { label: 'Tools',                 href: '/alternatives/agent-ai' },
        { label: 'Metrics',               href: '/leaderboard' },
        { label: 'FAQ',                   href: '/faq' },
        { label: 'Developers',            href: '/developers' },
        { label: 'Privacy',               href: '/privacy' },
        { label: 'Sitemap',               href: '/sitemap' },
      ],
    },
    {
      heading: 'Ecosystem',
      links: [
        { label: 'MO\u00a7ES\u2122',       href: 'https://mos2es.com',          ext: true },
        { label: 'SigArena',              href: 'https://sigeconomy.com',       ext: true },
        { label: 'SigRank',               href: 'https://signalaf.com',         ext: true },
        { label: 'GitHub',                href: 'https://github.com/SunrisesIllNeverSee', ext: true },
        { label: 'PyPI',                  href: 'https://pypi.org/project/civitae-mcp/',  ext: true },
        { label: 'ORCID',                 href: 'https://orcid.org/0009-0002-9904-5390',  ext: true },
        { label: 'Patent Info',           href: '/about' },
      ],
    },
  ];

  // ── Styles ─────────────────────────────────────────────────────────────────
  var styleEl = document.createElement('style');
  styleEl.id = 'signomy-footer-styles';
  styleEl.textContent = [
    /* Footer container */
    '#civitae-footer{',
    '  background:#0B0D10;',
    '  border-top:1px solid #1E2228;',
    '  padding:48px 32px 0;',
    '  font-family:"DM Sans",sans-serif;',
    '  color:#E8EAF0;',
    '  margin-top:auto;',
    '}',
    /* Top section: wordmark + columns */
    '.sf-top{max-width:1280px;margin:0 auto;display:flex;flex-direction:column;gap:40px;}',
    '.sf-brand{display:flex;align-items:baseline;gap:12px;}',
    '.sf-brand .sf-logo{font-family:"Playfair Display",serif;font-size:28px;font-weight:900;color:#C4923A;letter-spacing:0.01em;}',
    '.sf-brand .sf-logo em{font-style:italic;color:#E8EAF0;}',
    '.sf-brand .sf-tag{font-family:"DM Mono",monospace;font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;color:#7A8090;}',
    /* Columns grid */
    '.sf-cols{display:grid;grid-template-columns:repeat(6,1fr);gap:32px;}',
    '.sf-col{display:flex;flex-direction:column;gap:10px;}',
    '.sf-col h4{font-family:"DM Mono",monospace;font-size:0.62rem;letter-spacing:0.16em;text-transform:uppercase;color:#C4923A;margin:0 0 4px;font-weight:500;}',
    '.sf-col a{font-size:0.8rem;color:#7A8090;text-decoration:none;line-height:1.5;transition:color 0.15s;}',
    '.sf-col a:hover{color:#E8EAF0;}',
    /* Bottom bar */
    '.sf-bottom{max-width:1280px;margin:32px auto 0;padding:20px 0;border-top:1px solid #1E2228;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}',
    '.sf-copy{font-family:"DM Mono",monospace;font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#4A5060;}',
    '.sf-copy a{color:#4A5060;text-decoration:none;transition:color 0.15s;}',
    '.sf-copy a:hover{color:#C4923A;}',
    '.sf-social{display:flex;align-items:center;gap:14px;}',
    '.sf-social a{color:#4A5060;transition:color 0.15s;display:flex;align-items:center;}',
    '.sf-social a:hover{color:#C4923A;}',
    '.sf-social svg{display:block;}',
    /* Responsive: tablet → 2 columns */
    '@media(max-width:900px){',
    '  #civitae-footer{padding:36px 20px 0;}',
    '  .sf-cols{grid-template-columns:repeat(2,1fr);gap:28px;}',
    '}',
    /* Responsive: mobile → 1 column */
    '@media(max-width:600px){',
    '  #civitae-footer{padding:28px 16px 0;}',
    '  .sf-cols{grid-template-columns:1fr;gap:24px;}',
    '  .sf-bottom{flex-direction:column;align-items:flex-start;gap:12px;}',
    '}',
  ].join('\n');
  document.head.appendChild(styleEl);

  // ── Build footer DOM ───────────────────────────────────────────────────────
  function buildFooter() {
    var footer = document.createElement('footer');
    footer.id = 'civitae-footer';

    var top = document.createElement('div');
    top.className = 'sf-top';

    // Brand row
    var brand = document.createElement('div');
    brand.className = 'sf-brand';
    var logo = document.createElement('span');
    logo.className = 'sf-logo';
    logo.textContent = 'SIG';
    var em = document.createElement('em');
    em.textContent = 'NOMY';
    logo.appendChild(em);
    brand.appendChild(logo);
    var tag = document.createElement('span');
    tag.className = 'sf-tag';
    tag.textContent = 'Governed AI Agent City-State';
    brand.appendChild(tag);
    top.appendChild(brand);

    // Columns
    var cols = document.createElement('div');
    cols.className = 'sf-cols';

    COLUMNS.forEach(function (col) {
      var colEl = document.createElement('div');
      colEl.className = 'sf-col';
      var h = document.createElement('h4');
      h.textContent = col.heading;
      colEl.appendChild(h);
      col.links.forEach(function (l) {
        var a = document.createElement('a');
        a.href = l.href;
        a.textContent = l.label;
        if (l.ext) {
          a.target = '_blank';
          a.rel = 'noopener';
        }
        colEl.appendChild(a);
      });
      cols.appendChild(colEl);
    });
    top.appendChild(cols);
    footer.appendChild(top);

    // Bottom bar
    var bottom = document.createElement('div');
    bottom.className = 'sf-bottom';

    var copy = document.createElement('div');
    copy.className = 'sf-copy';
    copy.innerHTML = '\u00a9 2026 Ello Cello LLC \u00b7 Patent Pending 63/877,177 \u00b7 MO\u00a7ES\u2122 governs CIVITAE';
    bottom.appendChild(copy);

    // Social icons
    var social = document.createElement('div');
    social.className = 'sf-social';

    // GitHub
    var gh = document.createElement('a');
    gh.href = 'https://github.com/SunrisesIllNeverSee';
    gh.target = '_blank';
    gh.rel = 'noopener';
    gh.setAttribute('aria-label', 'GitHub');
    gh.appendChild(makeIcon('github'));
    social.appendChild(gh);

    // X / Twitter
    var x = document.createElement('a');
    x.href = 'https://x.com/signomyxyz';
    x.target = '_blank';
    x.rel = 'noopener';
    x.setAttribute('aria-label', 'X');
    x.appendChild(makeIcon('x'));
    social.appendChild(x);

    bottom.appendChild(social);
    footer.appendChild(bottom);

    return footer;
  }

  // ── SVG icon helper ────────────────────────────────────────────────────────
  function makeIcon(name) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '15');
    svg.setAttribute('height', '15');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'currentColor');
    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    if (name === 'github') {
      path.setAttribute('d', 'M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z');
    } else {
      path.setAttribute('d', 'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.259 5.629 5.905-5.629zm-1.161 17.52h1.833L7.084 4.126H5.117z');
    }
    svg.appendChild(path);
    return svg;
  }

  // ── Inject ─────────────────────────────────────────────────────────────────
  function inject() {
    // Remove any existing footer created by _nav.js or a previous load so we
    // always end up with exactly one rich footer.
    var existing = document.getElementById('civitae-footer');
    if (existing) existing.remove();

    // Also remove any orphaned style from _nav.js's inline footer styles.
    // (We keep our own #signomy-footer-styles.)

    var footer = buildFooter();
    document.body.appendChild(footer);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
}());
