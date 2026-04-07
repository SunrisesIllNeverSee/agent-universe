/**
 * SIGNOMY Global Nav — _nav.js
 * Inject via <script src="/assets/_nav.js"></script> in </head> of every content page.
 *
 * TWO-TIER LAYOUT:
 *   Top bar (64px): SIGNOMY wordmark left | 5 layer tabs right
 *   Sub-bar (36px): active layer's page links (or fallback links)
 *
 * Fixed-viewport pages (console, deploy, campaign, kingdoms) are in SKIP — own topbar.
 * To change layer tabs: edit layers[].name in pages.json
 * To change sub-links: edit layers[].navLinks in pages.json
 */
(function () {
  'use strict';

  // ── Google Analytics (GA4) ────────────────────────────────────────────────
  if (!document.getElementById('gtag-js')) {
    var gs = document.createElement('script');
    gs.id = 'gtag-js';
    gs.async = true;
    gs.src = 'https://www.googletagmanager.com/gtag/js?id=G-FD4VLSCHY8';
    document.head.appendChild(gs);
    window.dataLayer = window.dataLayer || [];
    function gtag(){window.dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-FD4VLSCHY8');
  }

  // ── NOMY typographic variants — randomly applied to <em>NOMY</em> each load ──
  var NOMY_VARIANTS = [
    // 1. Italic Playfair — the original happy accident
    { fontStyle:'italic',  fontFamily:'"Playfair Display",serif', fontWeight:'700',  letterSpacing:'0',       color:'#E8EAF0' },
    // 2. Upright monospace — cold and technical
    { fontStyle:'normal',  fontFamily:'"DM Mono",monospace',      fontWeight:'400',  letterSpacing:'0.08em',  color:'#E8EAF0' },
    // 3. Italic mono — strange and editorial
    { fontStyle:'italic',  fontFamily:'"DM Mono",monospace',      fontWeight:'400',  letterSpacing:'0.04em',  color:'#E8EAF0' },
    // 4. Sans light, spaced — architectural
    { fontStyle:'normal',  fontFamily:'"DM Sans",sans-serif',     fontWeight:'300',  letterSpacing:'0.22em',  color:'#E8EAF0' },
    // 5. Sans bold condensed — assertive
    { fontStyle:'normal',  fontFamily:'"DM Sans",sans-serif',     fontWeight:'700',  letterSpacing:'-0.02em', color:'#E8EAF0' },
    // 6. Italic Playfair gold — warm and regal
    { fontStyle:'italic',  fontFamily:'"Playfair Display",serif', fontWeight:'900',  letterSpacing:'0',       color:'#C4923A' },
  ];

  // ── Tab label overrides (shorter names for the top bar tabs) ─────────────────
  var TAB_LABELS = { 1:'Active', 2:'Context', 3:'Building' };

  // ── Skip fixed-viewport pages (they have their own topbar) ────────────────────
  var SKIP = ['/', '/kingdoms', '/console', '/deploy', '/campaign'];
  var path = window.location.pathname.replace(/\/$/, '') || '/';
  for (var s = 0; s < SKIP.length; s++) {
    if (path === SKIP[s]) return;
  }

  // ── Velvet Rope — client-side gate for protected pages ──────────────────────
  var GATED_PREFIXES = [
    '/console', '/command', '/agentdash', '/dashboard', '/deploy', '/campaign',
  ];
  var isGated = false;
  for (var g = 0; g < GATED_PREFIXES.length; g++) {
    if (path === GATED_PREFIXES[g] || path.indexOf(GATED_PREFIXES[g] + '/') === 0) {
      isGated = true;
      break;
    }
  }
  if (isGated) {
    fetch('/api/lobby/status', { credentials: 'include' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.status !== 'active') {
          window.location.href = '/lobby';
        }
      })
      .catch(function() {
        // API unreachable — let user through (fail open for now)
      });
  }

  // ── Fetch page data (cached in sessionStorage) ─────────────────────────────────
  function fetchPagesData() {
    var cached = null;
    try { cached = sessionStorage.getItem('_nav_pages'); } catch(e) {}
    if (cached) {
      try { return Promise.resolve(JSON.parse(cached)); } catch(e) {}
    }
    return fetch('/assets/pages.json').then(function(r) { return r.json(); }).then(function(d) {
      try { sessionStorage.setItem('_nav_pages', JSON.stringify(d)); } catch(e) {}
      return d;
    });
  }
  fetchPagesData().then(function(data) {
    var LAYERS = data.layers;
    var FALLBACK_LINKS = data.fallbackLinks;

  // ── Detect current layer ────────────────────────────────────────────────────
  function getCurrentLayer() {
    for (var i = 0; i < LAYERS.length; i++) {
      var layer = LAYERS[i];
      for (var j = 0; j < layer.paths.length; j++) {
        var p = layer.paths[j];
        var match = (p === '/') ? (path === '/') : (path === p || path.indexOf(p) === 0);
        if (match) return layer;
      }
    }
    return null;
  }

  // ── Font loading — skip if page already loads Playfair in <head> ──────────────
  // Most pages include Playfair via <link> already; only inject if missing.
  var hasPlayfair = false;
  var existingLinks = document.querySelectorAll('link[href*="Playfair"]');
  if (existingLinks.length > 0) hasPlayfair = true;
  if (!hasPlayfair && !document.getElementById('civitae-nav-fonts')) {
    var fontLink = document.createElement('link');
    fontLink.id   = 'civitae-nav-fonts';
    fontLink.rel  = 'stylesheet';
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap';
    document.head.appendChild(fontLink);
  }

  // ── Banner text from pages.json ───────────────────────────────────────────
  var SITE_BANNER = data.siteBanner || '';

  // ── Styles ───────────────────────────────────────────────────────────────────
  var styleEl = document.createElement('style');
  styleEl.id = 'civitae-nav-styles';
  styleEl.textContent = [

    /* Banner bar */
    '.cn-banner{height:28px;display:flex;align-items:center;justify-content:center;',
    'background:rgba(196,146,58,0.08);border-bottom:1px solid rgba(196,146,58,0.15);',
    'font-family:"DM Mono",monospace;font-size:0.62rem;letter-spacing:0.1em;',
    'text-transform:uppercase;color:#C4923A;padding:0 16px;gap:8px;overflow:hidden;',
    'white-space:nowrap;text-overflow:ellipsis;}',
    '.cn-banner-dot{width:6px;height:6px;border-radius:50%;background:#C4923A;',
    'flex-shrink:0;animation:cn-pulse 2s ease-in-out infinite;}',
    '@keyframes cn-pulse{0%,100%{opacity:0.4}50%{opacity:1}}',

    /* Nav wrapper — column, auto height */
    '#civitae-nav{position:fixed;top:0;left:0;right:0;height:auto;',
    'background:rgba(11,13,16,0.97);border-bottom:1px solid #1E2228;',
    'display:flex;flex-direction:column;align-items:stretch;',
    'z-index:9999;font-family:"DM Sans",sans-serif;',
    'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);}',

    /* ── Top bar ── */
    '.cn-top-bar{height:64px;display:flex;align-items:center;flex-shrink:0;}',

    /* Wordmark — dropdown trigger */
    '.cn-mark-wrap{position:relative;height:100%;flex-shrink:0;border-right:1px solid #1E2228;}',
    '.cn-mark-btn{',
    'font-family:"Playfair Display",serif;color:#C4923A;',
    'font-size:26px;font-weight:900;letter-spacing:0.01em;',
    'background:none;border:none;cursor:pointer;',
    'height:100%;padding:0 20px;display:flex;align-items:center;gap:7px;',
    'transition:background 0.15s;}',
    '.cn-mark-btn:hover{background:rgba(196,146,58,0.07);}',
    '.cn-mark-btn em{color:#E8EAF0;}',
    '.cn-mark-chevron{font-size:9px;color:#555;line-height:1;transition:transform 0.18s;}',
    '.cn-mark-wrap.open .cn-mark-chevron{transform:rotate(180deg);}',
    /* Dropdown panel */
    '.cn-mark-drop{display:none;position:absolute;top:calc(100% + 1px);left:0;',
    'min-width:200px;background:rgba(10,11,14,0.99);',
    'border:1px solid #1E2228;border-top:2px solid #C4923A;',
    'box-shadow:0 16px 40px rgba(0,0,0,0.7);z-index:10000;padding:6px 0;}',
    '.cn-mark-wrap.open .cn-mark-drop{display:block;}',
    '.cn-drop-link{display:block;font-family:"DM Mono",monospace;font-size:0.68rem;',
    'letter-spacing:0.1em;text-transform:uppercase;color:#7A8090;',
    'text-decoration:none;padding:10px 18px;transition:color 0.12s,background 0.12s;}',
    '.cn-drop-link:hover{color:#C4923A;background:rgba(196,146,58,0.06);}',
    '.cn-drop-divider{height:1px;background:#1E2228;margin:4px 0;}',

    /* Layer tabs — right side of top bar */
    '.cn-layers{display:flex;align-items:center;height:100%;margin-left:auto;}',
    '.cn-layer{',
    'font-family:"DM Mono",monospace;font-size:0.7rem;',
    'letter-spacing:0.1em;text-transform:uppercase;color:#7A8090;',
    'padding:0 18px;height:100%;display:flex;align-items:center;',
    'border-left:1px solid #1E2228;text-decoration:none;',
    'transition:color 0.15s,background 0.15s;',
    'box-sizing:border-box;}',
    '.cn-layer:hover{color:#E8EAF0;background:rgba(255,255,255,0.03);}',
    '.cn-layer.cn-active{color:#C4923A;border-bottom:2px solid #C4923A;}',

    /* ── Sub-bar ── */
    '.cn-sub-bar{',
    'height:36px;display:flex;align-items:center;',
    'border-top:1px solid #1E2228;padding:0 20px;',
    'background:rgba(9,11,14,0.95);}',
    '.cn-sub-link{',
    'font-family:"DM Sans",sans-serif;font-size:0.72rem;',
    'letter-spacing:0.06em;color:#5A6475;text-decoration:none;',
    'padding:0 14px;height:100%;display:flex;align-items:center;',
    'transition:color 0.15s;}',
    '.cn-sub-link:hover{color:#C4923A;}',
    '.cn-sub-link.cn-active{color:#E8EAF0;}',

  ].join('');
  document.head.appendChild(styleEl);

  // ── Build top bar ─────────────────────────────────────────────────────────────
  function buildTopBar(currentLayer) {
    var topBar = document.createElement('div');
    topBar.className = 'cn-top-bar';

    // Wordmark dropdown
    var markWrap = document.createElement('div');
    markWrap.className = 'cn-mark-wrap';

    var markBtn = document.createElement('button');
    markBtn.className = 'cn-mark-btn';
    markBtn.setAttribute('aria-expanded', 'false');
    markBtn.appendChild(document.createTextNode('SIG'));
    var em = document.createElement('em');
    em.textContent = 'NOMY';
    var v = NOMY_VARIANTS[Math.floor(Math.random() * NOMY_VARIANTS.length)];
    em.style.cssText = 'font-style:'+v.fontStyle+';font-family:'+v.fontFamily+';font-weight:'+v.fontWeight+';letter-spacing:'+v.letterSpacing+';color:'+v.color+';';
    markBtn.appendChild(em);
    var chevron = document.createElement('span');
    chevron.className = 'cn-mark-chevron';
    chevron.textContent = '▾';
    markBtn.appendChild(chevron);
    markWrap.appendChild(markBtn);

    // Dropdown panel
    var drop = document.createElement('div');
    drop.className = 'cn-mark-drop';
    var dropLinks = [
      { label: 'Portal',    href: '/portal' },
      { label: 'KA\u00a7\u00a7A \u2014 Marketplace', href: '/kassa' },
      { label: 'Advisory',  href: '/advisory' },
      { label: 'Contact',   href: '/contact' },
    ];
    dropLinks.forEach(function(l, i) {
      var a = document.createElement('a');
      a.className = 'cn-drop-link';
      a.href = l.href;
      a.textContent = l.label;
      drop.appendChild(a);
      if (i === 0) {
        var div = document.createElement('div');
        div.className = 'cn-drop-divider';
        drop.appendChild(div);
      }
    });
    markWrap.appendChild(drop);

    // Toggle open/close
    markBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var isOpen = markWrap.classList.toggle('open');
      markBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    document.addEventListener('click', function() {
      markWrap.classList.remove('open');
      markBtn.setAttribute('aria-expanded', 'false');
    });

    topBar.appendChild(markWrap);

    // Layer tabs
    var layers = document.createElement('div');
    layers.className = 'cn-layers';

    LAYERS.forEach(function(layer) {
      var label = TAB_LABELS[layer.id] || layer.name;
      var isActive = currentLayer && (currentLayer.id === layer.id);
      var a = document.createElement('a');
      a.href = layer.href;
      a.className = isActive ? 'cn-layer cn-active' : 'cn-layer';
      a.textContent = label;
      layers.appendChild(a);
    });

    topBar.appendChild(layers);
    return topBar;
  }

  // ── Build sub-bar ─────────────────────────────────────────────────────────────
  function buildSubBar(currentLayer) {
    var subBar = document.createElement('div');
    subBar.className = 'cn-sub-bar';

    var linkList = currentLayer ? currentLayer.navLinks : FALLBACK_LINKS;

    linkList.forEach(function(l) {
      var active = (l.href === '/')
        ? (path === '/')
        : (path === l.href || path.indexOf(l.href) === 0);
      var a = document.createElement('a');
      a.href = l.href;
      a.className = active ? 'cn-sub-link cn-active' : 'cn-sub-link';
      a.textContent = l.label;
      subBar.appendChild(a);
    });

    return subBar;
  }

  // ── Inject ───────────────────────────────────────────────────────────────────
  function inject() {
    var nav = document.getElementById('civitae-nav') || document.querySelector('nav');
    if (!nav) {
      nav = document.createElement('nav');
      document.body.insertBefore(nav, document.body.firstChild);
    }
    while (nav.firstChild) nav.removeChild(nav.firstChild);
    nav.id = 'civitae-nav';

    var currentLayer = getCurrentLayer();

    // Banner (if siteBanner is set in pages.json)
    var bannerHeight = 0;
    if (SITE_BANNER) {
      var banner = document.createElement('div');
      banner.className = 'cn-banner';
      var dot = document.createElement('span');
      dot.className = 'cn-banner-dot';
      banner.appendChild(dot);
      banner.appendChild(document.createTextNode(SITE_BANNER));
      nav.appendChild(banner);
      bannerHeight = 28;
    }

    nav.appendChild(buildTopBar(currentLayer));
    nav.appendChild(buildSubBar(currentLayer));

    // 64px top bar + 36px sub-bar + banner = total offset
    var totalHeight = 100 + bannerHeight;
    var current = parseInt(document.body.style.paddingTop) || 0;
    if (current < totalHeight) document.body.style.paddingTop = totalHeight + 'px';

    // ── Footer ───────────────────────────────────────────────────────────────
    if (!document.getElementById('civitae-footer')) {
      var footerStyle = document.createElement('style');
      footerStyle.textContent = '#civitae-footer{background:rgba(11,13,16,0.97);border-top:1px solid #1a1a22;height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;font-family:"DM Mono",monospace;font-size:8px;letter-spacing:0.18em;color:#3a3a4a;text-transform:uppercase;z-index:9998;}' +
        '#civitae-footer a{color:#3a3a4a;text-decoration:none;transition:color 0.15s;}' +
        '#civitae-footer a:hover{color:#c8a96e;}' +
        '#civitae-footer svg{display:block;}';
      document.head.appendChild(footerStyle);

      var footer = document.createElement('footer');
      footer.id = 'civitae-footer';

      var left = document.createElement('div');
      left.textContent = 'CIVITAE \u00b7 MO\u00a7ES\u2122 \u00b7 ELLO CELLO LLC \u00b7 \u00a9 2026 \u00b7 Patent Pending';
      footer.appendChild(left);

      var right = document.createElement('div');
      right.style.cssText = 'display:flex;align-items:center;gap:16px;';

      // GitHub icon
      var ghLink = document.createElement('a');
      ghLink.href = 'https://github.com/SunrisesIllNeverSee';
      ghLink.target = '_blank';
      ghLink.rel = 'noopener';
      var ghSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      ghSvg.setAttribute('width', '14');
      ghSvg.setAttribute('height', '14');
      ghSvg.setAttribute('viewBox', '0 0 24 24');
      ghSvg.setAttribute('fill', 'currentColor');
      var ghPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      ghPath.setAttribute('d', 'M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z');
      ghSvg.appendChild(ghPath);
      ghLink.appendChild(ghSvg);
      right.appendChild(ghLink);

      // X / Twitter icon
      var xLink = document.createElement('a');
      xLink.href = 'https://x.com/signomyxyz';
      xLink.target = '_blank';
      xLink.rel = 'noopener';
      var xSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      xSvg.setAttribute('width', '13');
      xSvg.setAttribute('height', '13');
      xSvg.setAttribute('viewBox', '0 0 24 24');
      xSvg.setAttribute('fill', 'currentColor');
      var xPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      xPath.setAttribute('d', 'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.259 5.629 5.905-5.629zm-1.161 17.52h1.833L7.084 4.126H5.117z');
      xSvg.appendChild(xPath);
      xLink.appendChild(xSvg);
      right.appendChild(xLink);

      footer.appendChild(right);
      document.body.appendChild(footer);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }

  }); // end fetch callback
}());
