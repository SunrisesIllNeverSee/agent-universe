// AI and search crawlers don't run JavaScript, so the PostHog snippet on the
// pages never sees them. middleware.js calls crawlerCapture() on each request
// and, for a known crawler, sends one `ai_bot_detected` event to PostHog after
// the response (waitUntil), so a page is never delayed or broken by analytics.
// Same event and properties as signalaf.com and mos2es.com, so one PostHog
// dashboard covers all three sites.

export const AI_CRAWLER_EVENT = "ai_bot_detected";

// The public project key the site's pages already embed (it is in every
// page's HTML, so it is not a secret). A POSTHOG_KEY variable overrides it.
const POSTHOG_PUBLIC_KEY = "phc_DosVqZCDFVNghfXCfLQBHG5ZpntSRmzrJZRzhKLMqTkh";
const POSTHOG_CAPTURE_URL = "https://us.i.posthog.com/i/v0/e/";

// Families:
// - ai_training: collects pages to train models
// - ai_search: builds an AI search index
// - ai_user_fetch: fetches a page live because a person asked an AI about it
// - search: classic search engine (Bing's index also feeds Copilot)
// Matched in order, case-insensitively, as a substring of the User-Agent.
const CRAWLERS = [
  ["OAI-SearchBot", "OpenAI", "ai_search"],
  ["ChatGPT-User", "OpenAI", "ai_user_fetch"],
  ["GPTBot", "OpenAI", "ai_training"],
  ["Claude-SearchBot", "Anthropic", "ai_search"],
  ["Claude-User", "Anthropic", "ai_user_fetch"],
  ["Claude-Web", "Anthropic", "ai_user_fetch"],
  ["ClaudeBot", "Anthropic", "ai_training"],
  ["anthropic-ai", "Anthropic", "ai_training"],
  ["Perplexity-User", "Perplexity", "ai_user_fetch"],
  ["PerplexityBot", "Perplexity", "ai_search"],
  ["DuckAssistBot", "DuckDuckGo", "ai_search"],
  ["YouBot", "You.com", "ai_search"],
  ["meta-externalfetcher", "Meta", "ai_user_fetch"],
  ["meta-externalagent", "Meta", "ai_training"],
  ["cohere-ai", "Cohere", "ai_training"],
  ["Bytespider", "ByteDance", "ai_training"],
  ["CCBot", "Common Crawl", "ai_training"],
  ["Amazonbot", "Amazon", "ai_training"],
  ["Diffbot", "Diffbot", "ai_training"],
  ["Googlebot", "Google", "search"],
  ["Bingbot", "Microsoft", "search"],
  ["Applebot", "Apple", "search"],
  ["DuckDuckBot", "DuckDuckGo", "search"],
  ["YandexBot", "Yandex", "search"],
  ["Baiduspider", "Baidu", "search"],
].map(([name, operator, family]) => ({ name, operator, family, needle: name.toLowerCase() }));

// Images, styles, scripts, fonts and media are skipped. Pages, robots.txt,
// llms.txt, sitemaps, .well-known JSON and Markdown are kept: which of those
// AI crawlers read is the point.
const SKIPPED_EXT = /\.(?:css|js|mjs|map|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|mp4|webm|mov|mp3|wav)$/i;

// Only the live site is recorded, so Vercel previews and local runs don't mix
// into the dashboard.
const PRODUCTION_HOSTS = new Set(["signomy.xyz", "www.signomy.xyz"]);

// Backend routes proxied to the API, and the operator console: never recorded.
const PRIVATE_PATH = /^\/(?:api|mcp|ws|admin|operator)(?:\/|$)/;

// The crawler named in a User-Agent, or null for people and unknown bots.
export function detectCrawler(userAgent) {
  if (!userAgent) return null;
  const ua = userAgent.toLowerCase();
  for (const crawler of CRAWLERS) {
    if (ua.includes(crawler.needle)) {
      const { name, operator, family } = crawler;
      return { name, operator, family };
    }
  }
  return null;
}

// The PostHog capture request for a crawler hit, or null when nothing should
// be sent: people, unknown bots, methods other than GET/HEAD, hosts other than
// signomy.xyz, assets and backend/operator routes. Bots are known by
// User-Agent only, so a client can claim to be one. The query string is never
// recorded.
export function crawlerCapture(request, env = {}) {
  if (request.method !== "GET" && request.method !== "HEAD") return null;
  const crawler = detectCrawler(request.headers.get("user-agent"));
  if (!crawler) return null;
  const url = new URL(request.url);
  const host = url.hostname.toLowerCase().replace(/\.$/, "");
  if (!PRODUCTION_HOSTS.has(host)) return null;
  const path = url.pathname;
  if (SKIPPED_EXT.test(path) || PRIVATE_PATH.test(path)) return null;
  const body = {
    api_key: env.POSTHOG_KEY || POSTHOG_PUBLIC_KEY,
    event: AI_CRAWLER_EVENT,
    // One PostHog id per bot, with no person profile: bots aren't people.
    distinct_id: `crawler:${crawler.name}`,
    timestamp: new Date().toISOString(),
    properties: {
      bot_name: crawler.name,
      bot_operator: crawler.operator,
      bot_family: crawler.family,
      host,
      path,
      method: request.method,
      $host: host,
      $pathname: path,
      $current_url: `https://${host}${path}`,
      $process_person_profile: false,
      $lib: "signomy-vercel-middleware",
    },
  };
  return {
    bot: crawler.name,
    url: POSTHOG_CAPTURE_URL,
    // No timeout signal here: middleware.js adds one when it calls fetch.
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  };
}
