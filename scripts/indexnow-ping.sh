#!/usr/bin/env bash
# IndexNow ping — notifies Bing, DuckDuckGo, Yandex, and Seznam
# about all URLs in the sitemap. Run after each deploy.
#
# Usage:
#   ./scripts/indexnow-ping.sh              # ping all URLs from sitemap
#   ./scripts/indexnow-ping.sh /treasury    # ping a single URL

set -euo pipefail

HOST="signomy.xyz"
KEY="036af2adecc34d87884249a062326a1e"
KEY_LOCATION="https://${HOST}/${KEY}.txt"
ENGINES=("api.indexnow.org" "www.bing.com" "yandex.com")

ping_urls() {
  local urls=("$@")
  local json_urls
  json_urls=$(printf '"%s",' "${urls[@]}")
  json_urls="[${json_urls%,}]"

  local payload
  payload=$(cat <<EOF
{
  "host": "${HOST}",
  "key": "${KEY}",
  "keyLocation": "${KEY_LOCATION}",
  "urlList": ${json_urls}
}
EOF
)

  for engine in "${ENGINES[@]}"; do
    echo "→ Pinging ${engine} with ${#urls[@]} URLs..."
    status=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST "https://${engine}/indexnow" \
      -H "Content-Type: application/json; charset=utf-8" \
      -d "${payload}")
    echo "  ${engine}: HTTP ${status}"
  done
}

if [ $# -gt 0 ]; then
  # Single URL mode
  url="https://${HOST}${1}"
  echo "Pinging single URL: ${url}"
  ping_urls "${url}"
else
  # Full sitemap mode — extract all <loc> URLs
  SITEMAP="frontend/sitemap.xml"
  if [ ! -f "${SITEMAP}" ]; then
    SITEMAP="$(dirname "$0")/../frontend/sitemap.xml"
  fi

  if [ ! -f "${SITEMAP}" ]; then
    echo "Error: sitemap.xml not found"
    exit 1
  fi

  mapfile -t urls < <(grep -oP '(?<=<loc>)https://[^<]+' "${SITEMAP}")
  echo "Found ${#urls[@]} URLs in sitemap"
  echo ""

  # IndexNow accepts max 10,000 URLs per request, batch in groups of 100
  batch_size=100
  for ((i=0; i<${#urls[@]}; i+=batch_size)); do
    batch=("${urls[@]:i:batch_size}")
    echo "--- Batch $((i/batch_size + 1)) (${#batch[@]} URLs) ---"
    ping_urls "${batch[@]}"
    echo ""
  done
fi

echo "Done."
