/**
 * _footer.js — Fixed-position footer for SKIP pages
 * (console, deploy, campaign, kingdoms, /)
 * Inject via <script src="/assets/_footer.js"></script> before </body>
 */
(function () {
  'use strict';
  if (document.getElementById('civitae-footer')) return;

  var styleEl = document.createElement('style');
  styleEl.textContent = '#civitae-footer{position:fixed;bottom:0;left:0;right:0;background:rgba(11,13,16,0.97);border-top:1px solid #1a1a22;height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;font-family:"DM Mono",monospace;font-size:8px;letter-spacing:0.18em;color:#3a3a4a;text-transform:uppercase;z-index:9998;}' +
    '#civitae-footer a{color:#3a3a4a;text-decoration:none;transition:color 0.15s;}' +
    '#civitae-footer a:hover{color:#c8a96e;}' +
    '#civitae-footer svg{display:block;}';
  document.head.appendChild(styleEl);

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

  function inject() { document.body.appendChild(footer); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
}());
