// Shared WebSocket base URL.
// Vercel rewrites proxy HTTP to Railway but cannot tunnel WS upgrades to an
// external host, so on the production static host the socket must go direct.
window.CIVITAE_WS_BASE = (function () {
  var proto = location.protocol === 'https:' ? 'wss' : 'ws';
  if (location.hostname === 'signomy.xyz' || location.hostname === 'www.signomy.xyz') {
    return 'wss://agent-universe-production.up.railway.app';
  }
  return proto + '://' + location.host;
})();
