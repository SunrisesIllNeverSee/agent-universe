// Vercel Routing Middleware: record AI and search crawler visits in PostHog.
// Runs in front of the static site; it never changes the response.
import { next, waitUntil } from "@vercel/functions";
import { crawlerCapture } from "./scripts/edge/ai-crawler.mjs";

// Skip images, styles, scripts, fonts and media so only pages and crawler
// files (robots.txt, llms.txt, sitemaps, .well-known) reach the middleware.
export const config = {
  matcher: [
    "/((?!assets/|.*\\.(?:css|js|mjs|map|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|mp4|webm|mov|mp3|wav)$).*)",
  ],
};

export default function middleware(request) {
  // Analytics must never delay or break the page, so every failure is swallowed.
  try {
    const capture = crawlerCapture(request, process.env);
    if (capture) {
      // Drain the PostHog response so the subrequest doesn't stall.
      waitUntil(
        fetch(capture.url, capture.init)
          .then((res) => res.body?.cancel())
          .catch(() => {}),
      );
    }
  } catch {
    // ignore
  }
  return next();
}
