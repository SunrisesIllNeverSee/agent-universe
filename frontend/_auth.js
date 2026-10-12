// _auth.js — shared operator-auth gate for cockpit pages.
// Login = agent_id + api_key, verified against /api/provision/status/{id}.
// Creds live in localStorage.civitas_auth ({ agentId, key, agentData }).
// Dashboard (/dashboard) is the canonical login surface — unauthenticated
// visitors are redirected there to connect.

window.CIVITAE_AUTH = (function () {
  'use strict';

  var STORAGE_KEY = 'civitas_auth';
  var LOGIN_PATH = '/dashboard';

  // Entry signup (/entry) stores the same agent's own provision key as
  // au_agent_id + au_api_key rather than civitas_auth. Read it as a fallback
  // so the shell and hosted cockpit pages agree on the acting principal.
  // Same door (provision api_key), still verified by verify(); never written.
  var FALLBACK_REJECTED = 'civitas_auth_fallback_rejected';

  function entryCreds() {
    try {
      var id = localStorage.getItem('au_agent_id');
      var key = localStorage.getItem('au_api_key');
      if (!id || !key) return null;
      if (sessionStorage.getItem(FALLBACK_REJECTED) === id) return null;
      return { agentId: id, key: key, agentData: null, source: 'entry' };
    } catch (e) { return null; }
  }

  function creds() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var c = JSON.parse(raw);
        if (c && c.agentId && c.key) return c;
      }
    } catch (e) {}
    return entryCreds();
  }

  function clear() {
    var c = creds();
    if (c && c.source === 'entry') {
      try { sessionStorage.setItem(FALLBACK_REJECTED, c.agentId); } catch (e) {}
      return;
    }
    localStorage.removeItem(STORAGE_KEY);
  }

  function headers() {
    var c = creds();
    return c ? { 'Authorization': 'Bearer ' + c.key } : {};
  }

  // Verify stored creds against the backend (same check dashboard uses).
  // Resolves creds on success; null on failure (and clears stale creds).
  function verify() {
    var c = creds();
    if (!c) return Promise.resolve(null);
    var base = window.CIVITAE_API_BASE || '';
    return fetch(base + '/api/provision/status/' + encodeURIComponent(c.agentId), {
      headers: { 'Authorization': 'Bearer ' + c.key }
    }).then(function (r) {
      if (!r.ok) { clear(); return null; }
      return c;
    }).catch(function () {
      // Backend unreachable — keep creds but treat as unauthenticated
      // for gating purposes (offline pages should still wall off).
      return null;
    });
  }

  // Page gate: call early in <head>. Hides the page until auth resolves —
  // no creds redirects immediately, stale creds redirect after verify.
  // Use: CIVITAE_AUTH.requireAuth().then(function(auth){ boot(); });
  function requireAuth() {
    document.documentElement.style.visibility = 'hidden';
    var c = creds();
    var back = encodeURIComponent(location.pathname + location.search);
    var login = LOGIN_PATH + '?next=' + back;
    if (!c) {
      location.href = login;
      return Promise.resolve(null);
    }
    return verify().then(function (ok) {
      if (!ok) { location.href = login; return null; }
      document.documentElement.style.visibility = '';
      return c;
    });
  }

  return { creds: creds, verify: verify, requireAuth: requireAuth, headers: headers, clear: clear };
})();
