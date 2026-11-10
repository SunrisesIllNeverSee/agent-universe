import assert from "node:assert/strict";
import test from "node:test";
import middleware, { config } from "../middleware.js";
import { AI_CRAWLER_EVENT, crawlerCapture, detectCrawler } from "../scripts/edge/ai-crawler.mjs";

const UA = {
  GPTBot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; +https://openai.com/gptbot",
  "OAI-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot",
  "ChatGPT-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
  ClaudeBot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
  "Claude-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-User/1.0; +Claude-User@anthropic.com)",
  "Claude-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +Searchbot@anthropic.com)",
  PerplexityBot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
  "Perplexity-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
  DuckAssistBot: "DuckAssistBot/1.2; (+http://duckduckgo.com/duckassistbot.html)",
  Googlebot: "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
  Bingbot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm) Chrome/116.0.1938.76 Safari/537.36",
  Applebot: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)",
  "meta-externalagent": "meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)",
  Bytespider: "Mozilla/5.0 (Linux; Android 5.0) AppleWebKit/537.36 (KHTML, like Gecko) Mobile Safari/537.36 (compatible; Bytespider; spider-feedback@bytedance.com)",
  CCBot: "CCBot/2.0 (https://commoncrawl.org/faq/)",
  Amazonbot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot) Chrome/119.0.6045.214 Safari/537.36",
  YouBot: "Mozilla/5.0 (compatible; YouBot (+http://www.you.com))",
  "cohere-ai": "cohere-ai",
};

const FAMILIES = {
  GPTBot: "ai_training", ClaudeBot: "ai_training", CCBot: "ai_training", Bytespider: "ai_training",
  "meta-externalagent": "ai_training", Amazonbot: "ai_training", "cohere-ai": "ai_training",
  "OAI-SearchBot": "ai_search", "Claude-SearchBot": "ai_search", PerplexityBot: "ai_search",
  DuckAssistBot: "ai_search", YouBot: "ai_search",
  "ChatGPT-User": "ai_user_fetch", "Claude-User": "ai_user_fetch", "Perplexity-User": "ai_user_fetch",
  Googlebot: "search", Bingbot: "search", Applebot: "search",
};

const BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";

const req = (url, userAgent, method = "GET") =>
  new Request(url, { method, headers: userAgent ? { "User-Agent": userAgent } : {} });

test("each real crawler user-agent is identified by name and family", () => {
  for (const [name, ua] of Object.entries(UA)) {
    const crawler = detectCrawler(ua);
    assert.equal(crawler?.name, name, ua);
    assert.equal(crawler.family, FAMILIES[name], name);
  }
});

test("people and unknown bots are not crawlers", () => {
  for (const ua of [null, "", BROWSER, "Slackbot-LinkExpanding 1.0", "Twitterbot/1.0", "SomeCrawler/1.0"]) {
    assert.equal(detectCrawler(ua), null, String(ua));
  }
});

test("a crawler hit builds one ai_bot_detected event with the shared property names and no query string", () => {
  const capture = crawlerCapture(req("https://signomy.xyz/products?utm_source=x&token=secret", UA["ChatGPT-User"]));
  assert.equal(capture.url, "https://us.i.posthog.com/i/v0/e/");
  assert.equal(capture.init.method, "POST");
  assert.equal(capture.bot, "ChatGPT-User");
  const body = JSON.parse(capture.init.body);
  assert.equal(body.event, AI_CRAWLER_EVENT);
  assert.equal(body.event, "ai_bot_detected");
  assert.equal(body.distinct_id, "crawler:ChatGPT-User");
  assert.match(body.api_key, /^phc_/);
  assert.deepEqual(body.properties, {
    bot_name: "ChatGPT-User",
    bot_operator: "OpenAI",
    bot_family: "ai_user_fetch",
    host: "signomy.xyz",
    path: "/products",
    method: "GET",
    $host: "signomy.xyz",
    $pathname: "/products",
    $current_url: "https://signomy.xyz/products",
    $process_person_profile: false,
    $lib: "signomy-vercel-middleware",
  });
  assert.doesNotMatch(capture.init.body, /utm_source|token|secret|\?/);
});

test("a POSTHOG_KEY variable overrides the embedded public key", () => {
  const body = JSON.parse(crawlerCapture(req("https://signomy.xyz/", UA.GPTBot), { POSTHOG_KEY: "phc_override" }).init.body);
  assert.equal(body.api_key, "phc_override");
});

test("people, link previews and unknown bots send nothing", () => {
  for (const ua of [null, "", BROWSER, "Slackbot-LinkExpanding 1.0", "Twitterbot/1.0", "SomeRandomCrawler/1.0 crawler"]) {
    assert.equal(crawlerCapture(req("https://signomy.xyz/", ua)), null, String(ua));
  }
});

test("previews, local runs, assets, backend and operator routes, and non-GET requests send nothing", () => {
  for (const host of ["agent-universe.vercel.app", "agent-universe-git-x.vercel.app", "localhost", "evil-signomy.xyz"]) {
    assert.equal(crawlerCapture(req(`https://${host}/`, UA.GPTBot)), null, host);
  }
  for (const path of ["/assets/app.js", "/logo.png", "/style.css", "/fonts/a.woff2", "/api/agents", "/mcp", "/mcp/tools", "/ws/live", "/admin", "/admin/keys", "/operator/console"]) {
    assert.equal(crawlerCapture(req(`https://signomy.xyz${path}`, UA.GPTBot)), null, path);
  }
  for (const method of ["POST", "PUT", "DELETE", "OPTIONS"]) {
    assert.equal(crawlerCapture(req("https://signomy.xyz/", UA.GPTBot, method)), null, method);
  }
});

test("pages and crawler files are recorded, including www and HEAD", () => {
  for (const path of ["/", "/products", "/robots.txt", "/llms.txt", "/sitemap-v2.xml", "/.well-known/agent.json", "/index.md", "/administration"]) {
    assert.ok(crawlerCapture(req(`https://signomy.xyz${path}`, UA.GPTBot)), path);
  }
  assert.ok(crawlerCapture(req("https://www.signomy.xyz/about", UA.Bingbot, "HEAD")));
});

// Run the middleware with a stubbed fetch and a waitUntil spy.
const run = async (url, userAgent, fetchImpl, { method = "GET" } = {}) => {
  const calls = [];
  const waited = [];
  const realFetch = globalThis.fetch;
  const realWarn = console.warn;
  const warnings = [];
  globalThis.fetch = (u, init) => { calls.push({ url: u, init }); return fetchImpl(u, init); };
  console.warn = (...a) => warnings.push(a.join(" "));
  try {
    const res = middleware(req(url, userAgent, method), { waitUntil: (p) => waited.push(p) });
    await Promise.all(waited);
    return { res, calls, waited, warnings };
  } finally {
    globalThis.fetch = realFetch;
    console.warn = realWarn;
  }
};
const ok = async () => new Response("ok");

test("a crawler makes exactly one PostHog fetch through waitUntil and the request continues", async () => {
  const { res, calls, waited } = await run("https://signomy.xyz/products?token=secret", UA.GPTBot, ok);
  assert.equal(res.headers.get("x-middleware-next"), "1");
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(waited.length, 1);
  assert.equal(calls[0].url, "https://us.i.posthog.com/i/v0/e/");
  assert.ok(calls[0].init.signal instanceof AbortSignal, "timeout signal is created at fetch time");
  assert.doesNotMatch(calls[0].init.body, /token|secret/);
});

test("a browser makes no fetch and the request continues", async () => {
  const { res, calls, waited } = await run("https://signomy.xyz/", BROWSER, ok);
  assert.equal(res.headers.get("x-middleware-next"), "1");
  assert.equal(calls.length, 0);
  assert.equal(waited.length, 0);
});

test("a PostHog failure never throws out of the middleware and warns without the key or user-agent", async () => {
  for (const impl of [
    () => { throw new Error("sync boom"); },
    async () => { throw new Error("rejected"); },
    async () => new Response("nope", { status: 503 }),
  ]) {
    const { res, warnings } = await run("https://signomy.xyz/", UA.GPTBot, impl);
    assert.equal(res.headers.get("x-middleware-next"), "1");
    assert.ok(warnings.length <= 1);
    for (const w of warnings) {
      assert.match(w, /GPTBot/);
      assert.doesNotMatch(w, /phc_|Mozilla/);
    }
  }
  const { warnings } = await run("https://signomy.xyz/", UA.GPTBot, async () => new Response("nope", { status: 503 }));
  assert.equal(warnings.length, 1);
});

test("a missing context never breaks the request", () => {
  assert.equal(middleware(req("https://signomy.xyz/", UA.GPTBot)).headers.get("x-middleware-next"), "1");
});

test("the matcher skips proxied backend routes and assets but keeps pages and crawler files", () => {
  const re = new RegExp(`^${config.matcher[0]}$`);
  for (const p of ["/api/x", "/mcp", "/mcp/tools", "/ws/live", "/docs", "/docs/x", "/health", "/admin", "/operator/c", "/assets/a.js", "/a.png", "/s.css"]) {
    assert.ok(!re.test(p), `${p} should be skipped`);
  }
  for (const p of ["/", "/products", "/robots.txt", "/llms.txt", "/sitemap-v2.xml", "/.well-known/agent.json", "/administration", "/documents"]) {
    assert.ok(re.test(p), `${p} should reach the middleware`);
  }
});
