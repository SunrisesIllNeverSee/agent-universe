/**
 * CIVITAE Global Nav — _nav.js
 * Inject via <script src="/assets/_nav.js"></script> in </head> of every content page.
 *
 * HEADER (right side): Shows 4 sub-links for whatever layer you're currently in.
 *   Falls back to top-level links on pages outside any layer (sitemap, admin, etc.)
 *
 * DROPDOWN (CIVITAE ▼): Layer directory — 5 cards, each with a brief description.
 *   No sub-links in the dropdown. It's a map, not a menu.
 *
 * To add/change layer sub-links: edit the LAYERS array below.
 * To change fallback links: edit FALLBACK_LINKS.
 * Fixed-viewport pages (console, deploy, campaign, 3d) are in SKIP — own topbar.
 */
(function () {
  'use strict';

  // ── TAE typographic variants — randomly applied each page load ───────────────
  var TAE_VARIANTS = [
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

  // ── Skip fixed-viewport pages (they have their own topbar) ────────────────────
  var SKIP = ['/console', '/deploy', '/campaign', '/3d'];
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
    /* Nav bar */
    '#civitae-nav{position:fixed;top:0;left:0;right:0;height:64px;',
    'background:rgba(11,13,16,0.97);border-bottom:1px solid #1E2228;',
    'display:flex;align-items:center;padding:0;',
    'z-index:9999;font-family:"DM Sans",sans-serif;',
    'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);}',

    /* CIVITAE wordmark + dropdown trigger */
    '.cn-site-menu{position:relative;flex-shrink:0;height:100%;display:flex;align-items:center;}',
    '.cn-mark-btn{background:none;border:none;border-right:1px solid #1E2228;',
    'font-family:"Playfair Display",serif;color:#C4923A;',
    'font-size:26px;font-weight:900;letter-spacing:0.01em;cursor:pointer;',
    'height:100%;padding:0 20px;display:flex;align-items:center;gap:6px;',
    'transition:background 0.15s;}',
    '.cn-mark-btn:hover{background:rgba(196,146,58,0.07);}',
    '.cn-mark-btn em{color:#E8EAF0;}', /* base — specific style applied randomly via JS */
    '.cn-chevron{font-size:0.58rem;color:#7A8090;transition:transform 0.2s;line-height:1;margin-top:1px;}',
    '.cn-mark-btn.open .cn-chevron{transform:rotate(180deg);}',

    /* Dropdown panel */
    '.cn-dropdown{display:none;position:absolute;top:calc(100% + 1px);left:0;',
    'width:560px;background:#0D1014;border:1px solid #232830;',
    'border-top:2px solid #C4923A;box-shadow:0 24px 56px rgba(0,0,0,0.75);',
    'z-index:10000;padding:10px 0 8px;}',
    '.cn-dropdown.open{display:block;}',
    '.cn-dd-cols{display:grid;grid-template-columns:1fr 1fr;gap:0;}',
    '.cn-dd-col{padding:0 12px 4px;}',
    '.cn-dd-col+.cn-dd-col{border-left:1px solid #1E2228;}',

    /* Layer cards (dropdown) */
    '.cn-dd-card{display:block;text-decoration:none;padding:9px 10px;border-radius:3px;',
    'border:1px solid transparent;transition:background 0.15s,border-color 0.15s;margin-bottom:3px;}',
    '.cn-dd-card:hover{background:rgba(196,146,58,0.05);border-color:rgba(196,146,58,0.14);}',
    '.cn-dd-card-num{font-family:"DM Mono",monospace;font-size:0.52rem;',
    'letter-spacing:0.12em;color:#5A6475;text-transform:uppercase;}',
    '.cn-dd-card-title{font-family:"DM Mono",monospace;font-size:0.64rem;',
    'letter-spacing:0.1em;color:#C4923A;text-transform:uppercase;margin-top:2px;}',
    '.cn-dd-card:hover .cn-dd-card-title{color:#E8C06A;}',
    '.cn-dd-card-desc{font-family:"DM Sans",sans-serif;font-size:0.7rem;',
    'color:#B8C0CC;line-height:1.45;margin-top:4px;}',
    '.cn-dd-card:hover .cn-dd-card-desc{color:#E0E4EA;}',

    /* Dropdown footer */
    '.cn-dd-footer{border-top:1px solid #1E2228;margin-top:6px;padding:7px 14px 0;',
    'display:flex;justify-content:space-between;align-items:center;}',
    '.cn-dd-footer a{font-family:"DM Mono",monospace;font-size:0.62rem;color:#5A6070;',
    'text-decoration:none;transition:color 0.15s;}',
    '.cn-dd-footer a:hover{color:#C4923A;}',
    '.cn-dd-version{font-family:"DM Mono",monospace;font-size:0.58rem;color:#3a4050;}',

    /* Right-side nav links (layer-specific or fallback) */
    '.cn-links{display:flex;align-items:center;height:100%;margin-left:auto;}',
    '.cn-link{color:#7A8090;font-size:0.8rem;letter-spacing:0.08em;',
    'text-transform:uppercase;text-decoration:none;',
    'padding:0 16px;height:100%;display:flex;align-items:center;',
    'border-left:1px solid #1E2228;transition:color 0.15s,background 0.15s;}',
    '.cn-link:hover{color:#E8EAF0;background:rgba(255,255,255,0.03);}',
    '.cn-link.cn-active{color:#C4923A;}',
  ].join('');
  document.head.appendChild(styleEl);

  // ── Build dropdown — layer directory cards ────────────────────────────────────
  function buildDropdown() {
    var dd = document.createElement('div');
    dd.className = 'cn-dropdown';
    dd.id = 'cn-dropdown';

    var cols = document.createElement('div');
    cols.className = 'cn-dd-cols';

    var col1 = document.createElement('div'); col1.className = 'cn-dd-col';
    var col2 = document.createElement('div'); col2.className = 'cn-dd-col';

    LAYERS.forEach(function (layer, i) {
      var card = document.createElement('a');
      card.href = layer.href;
      card.className = 'cn-dd-card';
      card.onclick = function () { closeDropdown(); };

      var num = document.createElement('div');
      num.className = 'cn-dd-card-num';
      num.textContent = 'LAYER ' + layer.id;

      var title = document.createElement('div');
      title.className = 'cn-dd-card-title';
      title.textContent = '\u2014 ' + layer.name;

      var desc = document.createElement('div');
      desc.className = 'cn-dd-card-desc';
      desc.textContent = layer.desc;

      card.appendChild(num);
      card.appendChild(title);
      card.appendChild(desc);

      (i < 3 ? col1 : col2).appendChild(card);
    });

    cols.appendChild(col1);
    cols.appendChild(col2);

    var footer = document.createElement('div');
    footer.className = 'cn-dd-footer';
    var mapLink = document.createElement('a');
    mapLink.href = '/sitemap';
    mapLink.textContent = 'Full Sitemap \u2192';
    mapLink.onclick = function () { closeDropdown(); };
    var ver = document.createElement('span');
    ver.className = 'cn-dd-version';
    ver.textContent = 'CIVITAE \u00b7 2026';
    footer.appendChild(mapLink);
    footer.appendChild(ver);

    dd.appendChild(cols);
    dd.appendChild(footer);
    return dd;
  }

  // ── Build nav ─────────────────────────────────────────────────────────────────
  function buildNav() {
    // Wordmark + dropdown trigger
    var siteMenu = document.createElement('div');
    siteMenu.className = 'cn-site-menu';

    var btn = document.createElement('button');
    btn.className = 'cn-mark-btn';
    btn.id = 'cn-mark-btn';
    btn.appendChild(document.createTextNode('CIVI'));
    var em = document.createElement('em');
    em.textContent = 'TAE';
    var tae = TAE_VARIANTS[Math.floor(Math.random() * TAE_VARIANTS.length)];
    em.style.cssText = 'font-style:'+tae.fontStyle+';font-family:'+tae.fontFamily+';font-weight:'+tae.fontWeight+';letter-spacing:'+tae.letterSpacing+';color:'+tae.color+';';
    btn.appendChild(em);
    var chev = document.createElement('span'); chev.className = 'cn-chevron'; chev.textContent = '\u25bc';
    btn.appendChild(chev);
    btn.onclick = toggleDropdown;

    siteMenu.appendChild(btn);
    siteMenu.appendChild(buildDropdown());

    // Layer-specific or fallback right-side links
    var linksDiv = document.createElement('div');
    linksDiv.className = 'cn-links';

    var currentLayer = getCurrentLayer();
    var linkList = currentLayer ? currentLayer.navLinks : FALLBACK_LINKS;

    // Layer name as header anchor — always first, links to layer root so you can reset
    if (currentLayer) {
      var ovActive = (currentLayer.href === '/') ? (path === '/') : (path === currentLayer.href);
      var ovA = document.createElement('a');
      ovA.href = currentLayer.href;
      ovA.className = ovActive ? 'cn-link cn-active' : 'cn-link';
      ovA.textContent = currentLayer.name;
      linksDiv.appendChild(ovA);
    }

    linkList.forEach(function (l) {
      var active = (l.href === '/')
        ? (path === '/')
        : (path === l.href || path.indexOf(l.href) === 0);
      var a = document.createElement('a');
      a.href = l.href;
      a.className = active ? 'cn-link cn-active' : 'cn-link';
      a.textContent = l.label;
      linksDiv.appendChild(a);
    });

    return { siteMenu: siteMenu, links: linksDiv };
  }

  // ── Dropdown toggle ───────────────────────────────────────────────────────────
  function toggleDropdown() {
    var dd = document.getElementById('cn-dropdown');
    if (!dd) return;
    dd.classList.contains('open') ? closeDropdown() : openDropdown();
  }
  function openDropdown() {
    var btn = document.getElementById('cn-mark-btn');
    var dd  = document.getElementById('cn-dropdown');
    if (btn) btn.classList.add('open');
    if (dd)  dd.classList.add('open');
  }
  function closeDropdown() {
    var btn = document.getElementById('cn-mark-btn');
    var dd  = document.getElementById('cn-dropdown');
    if (btn) btn.classList.remove('open');
    if (dd)  dd.classList.remove('open');
  }

  document.addEventListener('click', function (e) {
    var menu = document.querySelector('.cn-site-menu');
    if (menu && !menu.contains(e.target)) closeDropdown();
  });

  // ── Inject ───────────────────────────────────────────────────────────────────
  function inject() {
    var nav = document.getElementById('civitae-nav') || document.querySelector('nav');
    if (!nav) {
      nav = document.createElement('nav');
      document.body.insertBefore(nav, document.body.firstChild);
    }
    while (nav.firstChild) nav.removeChild(nav.firstChild);
    nav.id = 'civitae-nav';

    var parts = buildNav();
    nav.appendChild(parts.siteMenu);
    nav.appendChild(parts.links);

    var current = parseInt(document.body.style.paddingTop) || 0;
    if (current < 64) document.body.style.paddingTop = '64px';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }

  }); // end fetch callback
}());
