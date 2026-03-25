(function () {
  'use strict';
  var isLocal = /^(localhost|127\.0\.0\.1)$/i.test(window.location.hostname);
  window.CIVITAE_API_ORIGIN = window.CIVITAE_API_ORIGIN
    || window.localStorage.getItem('civitae_api_origin')
    || (isLocal ? window.location.origin : 'https://web-production-08828.up.railway.app');
})();
