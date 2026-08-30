/**
 * MO§ES™ AI Analytics Beacon — standalone version for SKIP pages
 * Tracks AI crawler citations, AI referrer detection, and Core Web Vitals
 * Sends to the MO§ES™ analytics worker (cross-origin, CORS enabled)
 */
(function() {
  var ua = navigator.userAgent;
  var path = location.pathname;
  var BEACON_URL = 'https://mos2es.org/api/analytics/beacon';

  var aiBots = ['gptbot','oai-searchbot','chatgpt-user','perplexitybot','claudebot','anthropic-ai','google-extended','bingbot','ccbot','bytespider','applebot'];
  var isAiBot = aiBots.some(function(b) { return ua.toLowerCase().includes(b); });
  if (isAiBot) return;

  function beacon(type, data) {
    var payload = Object.assign({ type: type, path: path, site: 'signomy.xyz' }, data || {});
    try {
      fetch(BEACON_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(function() {});
    } catch(e) {}
  }

  beacon('pageview', { referrer: document.referrer || null });

  var aiReferrers = {
    'chatgpt.com': 'OpenAI/ChatGPT',
    'perplexity.ai': 'Perplexity',
    'claude.ai': 'Anthropic/Claude',
    'gemini.google.com': 'Google/Gemini',
    'copilot.microsoft.com': 'Microsoft/Copilot',
    'you.com': 'You.com',
    'phind.com': 'Phind',
    'kagi.com': 'Kagi',
  };
  for (var domain in aiReferrers) {
    if (document.referrer && document.referrer.includes(domain)) {
      beacon('ai_overview', {
        aiEngine: aiReferrers[domain],
        aiCited: true,
        referrer: document.referrer,
      });
      break;
    }
  }

  var vitals = { lcp: null, inp: null, cls: 0, ttfb: null };
  var vitalsSent = false;
  function sendVitals() {
    if (vitalsSent) return;
    vitalsSent = true;
    var navTiming = performance.getEntriesByType('navigation')[0];
    if (navTiming) {
      vitals.ttfb = Math.round(navTiming.responseStart - navTiming.requestStart);
    }
    beacon('web_vitals', vitals);
  }
  try {
    new PerformanceObserver(function(l) {
      var entries = l.getEntries();
      if (entries.length > 0) vitals.lcp = Math.round(entries[entries.length - 1].startTime);
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch(e) {}
  try {
    new PerformanceObserver(function(l) {
      l.getEntries().forEach(function(e) { if (!e.hadRecentInput) vitals.cls += e.value; });
    }).observe({ type: 'layout-shift', buffered: true });
  } catch(e) {}
  try {
    var maxDuration = 0;
    new PerformanceObserver(function(l) {
      l.getEntries().forEach(function(e) { if (e.duration > maxDuration) maxDuration = e.duration; });
      vitals.inp = Math.round(maxDuration);
    }).observe({ type: 'event', buffered: true });
  } catch(e) {}
  window.addEventListener('pagehide', function() {
    try {
      var payload = JSON.stringify(Object.assign({ type: 'web_vitals', path: path, site: 'signomy.xyz' }, vitals));
      navigator.sendBeacon(BEACON_URL, new Blob([payload], { type: 'application/json' }));
    } catch(e) { sendVitals(); }
  });
  setTimeout(sendVitals, 10000);
})();
