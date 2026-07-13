#!/bin/bash
# scripts/sf-crawl.sh — Run a Screaming Frog SEO crawl from the CLI
#
# Usage:
#   bash scripts/sf-crawl.sh              # crawl signomy.xyz, save to docs/sf-crawl-*/
#   bash scripts/sf-crawl.sh https://example.com  # crawl a different site
#
# Requirements:
#   - Screaming Frog SEO Spider installed in /Applications (macOS)
#   - License key configured in SF GUI (free tier: 500 URLs, paid: unlimited)
#
# Output:
#   docs/sf-crawl-<date>/<timestamp>/  — all CSV exports + crawl file
#   docs/sf-crawl-<date>/SF_ANALYSIS-<date>.md  — (you write this after)

set -euo pipefail

SITE="${1:-https://signomy.xyz}"
SF_APP="/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE=$(date +%Y.%m.%d)
TIMESTAMP=$(date +%Y.%m.%d.%H.%M.%S)
OUTPUT_DIR="${REPO_ROOT}/docs/sf-crawl-${DATE}"

if [ ! -f "$SF_APP" ]; then
  echo "ERROR: Screaming Frog not found at $SF_APP"
  echo "Install from https://www.screamingfrog.co.uk/seo-spider/"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "  Screaming Frog CLI Crawl"
echo "  Site:      $SITE"
echo "  Output:    $OUTPUT_DIR/$TIMESTAMP/"
echo "  Timestamp: $TIMESTAMP"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Run the crawl in headless mode with all bulk exports
"$SF_APP" \
  --headless \
  --crawl "$SITE" \
  --output-folder "$OUTPUT_DIR" \
  --timestamped-output \
  --overwrite \
  --save-crawl \
  --export-format csv \
  --bulk-export \
"Internal:All,External:All,Links:All Inlinks,Links:All Outlinks,Links:External Links,Response Codes:Internal:Internal Client Error (4xx) Inlinks,Response Codes:Internal:Internal Server Error (5xx) Inlinks,Response Codes:Internal:Internal Redirection (3xx) Inlinks,Response Codes:Internal:Internal Redirect Chain Inlinks,Security:Unsafe Cross-Origin Links,Security:HTTPS URLs Inlinks,Security:HTTP URLs Inlinks,Security:Mixed Content,Web:All Page Source,Web:All Page Text" \
  --save-report \
"Overview,Redirects,Blocked Resources,Response Codes,URI Issues,Title Tags,Meta Description,Meta Keywords,Meta Robots,Canonical Tags,Hreflang,Headings,Structured Data,Content,Links,Images,Page Speed,Mobile,JavaScript,Security,Sitemaps,Amp,Analytics,Crawl Analysis" \
  2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Crawl complete!"
echo "  Output: $OUTPUT_DIR/"
echo ""
echo "  Next steps:"
echo "    1. Review the CSV exports in the timestamped folder"
echo "    2. Write an ANALYSIS.md with YAML frontmatter"
echo "    3. Commit: git add docs/sf-crawl-${DATE}/ && git commit"
echo "═══════════════════════════════════════════════════════════════"
