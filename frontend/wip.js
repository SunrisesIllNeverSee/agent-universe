/**
 * CIVITAE — Under Construction Banner
 * Add <script src="/wip.js"></script> to any page that isn't ready.
 * Remove the script tag when the page is complete.
 */
(function () {
  var banner = document.createElement('div');
  banner.id = 'wip-banner';
  banner.style.cssText = [
    'position:fixed',
    'top:52px',        /* sits just below the nav */
    'left:0',
    'right:0',
    'z-index:9999',
    'background:repeating-linear-gradient(45deg,#1a0a00,#1a0a00 10px,#251000 10px,#251000 20px)',
    'border-top:2px solid #C4923A',
    'border-bottom:2px solid #C4923A',
    'color:#C4923A',
    'font-family:"DM Mono",monospace',
    'font-size:0.78rem',
    'letter-spacing:0.12em',
    'text-align:center',
    'padding:8px 16px',
    'display:flex',
    'align-items:center',
    'justify-content:center',
    'gap:12px',
  ].join(';');

  var icon = document.createElement('span');
  icon.textContent = '⚠';
  icon.style.fontSize = '1rem';

  var text = document.createElement('span');
  text.textContent = 'THIS PAGE IS UNDER CONSTRUCTION — CHECK BACK SOON';

  var close = document.createElement('button');
  close.textContent = '✕';
  close.style.cssText = [
    'background:none',
    'border:1px solid #C4923A',
    'color:#C4923A',
    'cursor:pointer',
    'font-size:0.7rem',
    'padding:2px 7px',
    'margin-left:12px',
    'font-family:inherit',
    'letter-spacing:0.08em',
  ].join(';');
  close.onclick = function () { banner.remove(); };

  banner.appendChild(icon);
  banner.appendChild(text);
  banner.appendChild(close);

  /* Push page body down so content isn't hidden under banner */
  var style = document.createElement('style');
  style.textContent = 'body { margin-top: 36px !important; }';

  document.addEventListener('DOMContentLoaded', function () {
    document.head.appendChild(style);
    document.body.insertBefore(banner, document.body.firstChild);
  });
})();
