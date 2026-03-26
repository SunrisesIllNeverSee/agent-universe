// kassa-api.js — KASSA board API client
// Set KASSA_API_BASE in your environment to point at the Railway backend.
// Falls back to relative URLs (works when frontend is served by FastAPI directly).
//
// Usage:
//   <script>window.KASSA_API_BASE = 'https://your-app.railway.app';</script>
//   <script src="/assets/kassa-api.js"></script>

(function (global) {
  'use strict';

  function base() {
    return (global.KASSA_API_BASE || '').replace(/\/$/, '');
  }

  var KassaAPI = {
    // ── Posts ────────────────────────────────────────────────────────────────

    /** Fetch published posts. All params optional. */
    getPosts: function (opts) {
      opts = opts || {};
      var params = new URLSearchParams();
      if (opts.tab)    params.set('tab', opts.tab);
      if (opts.status) params.set('status', opts.status);
      if (opts.sort)   params.set('sort', opts.sort);
      var qs = params.toString() ? '?' + params.toString() : '';
      return fetch(base() + '/api/kassa/posts' + qs)
        .then(function (r) { return r.json(); });
    },

    /** Fetch a single post by ID. */
    getPost: function (postId) {
      return fetch(base() + '/api/kassa/posts/' + postId)
        .then(function (r) {
          if (!r.ok) throw new Error('Post not found');
          return r.json();
        });
    },

    /** Submit a new post (goes to operator review queue). */
    submitPost: function (payload) {
      return fetch(base() + '/api/kassa/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then(function (r) { return r.json(); });
    },

    /** Upvote a post by ID. */
    upvote: function (postId) {
      return fetch(base() + '/api/kassa/posts/' + postId + '/upvote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }).then(function (r) { return r.json(); });
    },

    // ── Contact ──────────────────────────────────────────────────────────────

    /** Send a contact message for a post. */
    contact: function (payload) {
      return fetch(base() + '/api/kassa/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then(function (r) { return r.json(); });
    },
  };

  global.KassaAPI = KassaAPI;
})(window);
