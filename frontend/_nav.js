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
  var SKIP = ['/kingdoms', '/console', '/deploy', '/campaign'];
  var path = window.location.pathname.replace(/\/$/, '') || '/';
  for (var s = 0; s < SKIP.length; s++) {
    if (path === SKIP[s]) return;
  }

  // ── Fetch page data, then build ───────────────────────────────────────────────
  fetch('/assets/pages.json').then(function(r) { return r.json(); }).then(function(data) {
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

  // ── Load Playfair Display ─────────────────────────────────────────────────────
  if (!document.getElementById('civitae-nav-fonts')) {
    var fontLink = document.createElement('link');
    fontLink.id   = 'civitae-nav-fonts';
    fontLink.rel  = 'stylesheet';
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap';
    document.head.appendChild(fontLink);
  }

  // ── Styles ───────────────────────────────────────────────────────────────────
  var styleEl = document.createElement('style');
  styleEl.id = 'civitae-nav-styles';
  styleEl.textContent = [

    /* Nav wrapper — column, auto height */
    '#civitae-nav{position:fixed;top:0;left:0;right:0;height:auto;',
    'background:rgba(11,13,16,0.97);border-bottom:1px solid #1E2228;',
    'display:flex;flex-direction:column;align-items:stretch;',
    'z-index:9999;font-family:"DM Sans",sans-serif;',
    'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);}',

    /* ── Top bar ── */
    '.cn-top-bar{height:64px;display:flex;align-items:center;flex-shrink:0;}',

    /* Wordmark — <a> link, no button, no chevron */
    '.cn-mark-link{',
    'font-family:"Playfair Display",serif;color:#C4923A;',
    'font-size:26px;font-weight:900;letter-spacing:0.01em;',
    'text-decoration:none;border-right:1px solid #1E2228;',
    'height:100%;padding:0 20px;display:flex;align-items:center;flex-shrink:0;',
    'transition:background 0.15s;}',
    '.cn-mark-link:hover{background:rgba(196,146,58,0.07);}',
    '.cn-mark-link em{color:#E8EAF0;}', /* base color — specific style applied randomly via JS */

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

    // Wordmark link
    var mark = document.createElement('a');
    mark.className = 'cn-mark-link';
    mark.href = '/';
    mark.appendChild(document.createTextNode('SIG'));
    var em = document.createElement('em');
    em.textContent = 'NOMY';
    var v = NOMY_VARIANTS[Math.floor(Math.random() * NOMY_VARIANTS.length)];
    em.style.cssText = 'font-style:'+v.fontStyle+';font-family:'+v.fontFamily+';font-weight:'+v.fontWeight+';letter-spacing:'+v.letterSpacing+';color:'+v.color+';';
    mark.appendChild(em);
    topBar.appendChild(mark);

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
    nav.appendChild(buildTopBar(currentLayer));
    nav.appendChild(buildSubBar(currentLayer));

    // 64px top bar + 36px sub-bar = 100px total offset
    var current = parseInt(document.body.style.paddingTop) || 0;
    if (current < 100) document.body.style.paddingTop = '100px';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }

  }); // end fetch callback
}());
