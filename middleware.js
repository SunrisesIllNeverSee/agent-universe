// Vercel Routing Middleware: record AI and search crawler visits in PostHog.
// Runs in front of the static site; it never changes the response.
import { crawlerCapture } from "./scripts/edge/ai-crawler.mjs";

// The first matcher skips backend routes for crawler analytics; the explicit
// additional matchers intercept them to fail closed on preview deployments.
// Skip proxied backend routes (api, mcp, ws, docs, health, admin, operator),
// assets, and images, styles, scripts, fonts and media, so only pages and
// crawler files (robots.txt, llms.txt, sitemaps, .well-known) reach the
// middleware. The same private paths are also refused in crawlerCapture().
export const config = {
  matcher: [
    "/((?!(?:api|mcp|ws|admin|operator|docs|health|assets)(?:/|$)|.*\\.(?:css|js|mjs|map|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|mp4|webm|mov|mp3|wav)$).*)",
    "/api/:path*",
    "/mcp", "/mcp/:path*",
    "/docs", "/docs/:path*", "/health",
    "/ws/:path*",
  ],
};

// Same as next() from @vercel/functions (which sets exactly this header and an
// empty body): continue the request unchanged.
const proceed = () => new Response(null, { headers: { "x-middleware-next": "1" } });

// The static vercel.json API rewrites point at production. Until a genuinely
// isolated preview backend is available, *never* let preview traffic reach them.
// This is a preview gate, not an origin-auth mechanism for direct Railway calls.
const PREVIEW_BACKEND = /^\/(?:api|mcp|docs|health|ws)(?:\/|$)/;

export default function middleware(request, context) {
  const path = new URL(request.url).pathname;
  if (PREVIEW_BACKEND.test(path) && process.env.VERCEL_ENV !== "production") {
    return new Response(JSON.stringify({ error: "preview_backend_unavailable" }), {
      status: 503,
      headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store",
                 "x-signomy-preview-isolation": "blocked" },
    });
  }
  // Analytics must never delay or break the page, so every failure is swallowed.
  try {
    const capture = crawlerCapture(request, process.env);
    if (capture && typeof context?.waitUntil === "function") {
      const sent = fetch(capture.url, {
        ...capture.init,
        // Never let a slow PostHog hold the function open.
        signal: AbortSignal.timeout(5000),
      })
        .then((res) => {
          if (!res.ok) console.warn(`ai-crawler: PostHog returned ${res.status} for ${capture.bot}`);
          // Drain the response so the subrequest doesn't stall.
          return res.body?.cancel();
        })
        .catch((err) => console.warn(`ai-crawler: PostHog send failed for ${capture.bot}: ${err?.name ?? "error"}`))
        .catch(() => {});
      context.waitUntil(sent);
    }
  } catch {
    // ignore
  }
  return proceed();
}
