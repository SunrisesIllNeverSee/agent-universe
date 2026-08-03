#!/usr/bin/env bash
# IndexNow ping script for signomy.xyz
# Notifies Bing, DuckDuckGo, Yandex about page updates.
#
# Usage:
#   ./scripts/indexnow-ping.sh            # ping all sitemap URLs
#   ./scripts/indexnow-ping.sh /kassa     # ping a single URL

set -euo pipefail

HOST="signomy.xyz"
KEY="51976fa8a5d2128a98a52af6b05d2141"
KEY_LOCATION="https://${HOST}/${KEY}.txt"
SITEMAP_URL="https://${HOST}/sitemap-v2.xml"

ENGINES=(
  "https://api.indexnow.org/indexnow"
  "https://www.bing.com/indexnow"
  "https://yandex.com/indexnow"
)

if [ "${1:-}" != "" ]; then
  URLS=("https://${HOST}${1}")
else
  echo "Fetching sitemap from $SITEMAP_URL..."
  mapfile -t URLS < <(curl -s "$SITEMAP_URL" | sed -n 's/.*<loc>\(.*\)<\/loc>.*/\1/p')
fi

if [ ${#URLS[@]} -eq 0 ]; then
  echo "ERROR: No URLs found" >&2
  exit 1
fi

echo "Pinging ${#URLS[@]} URL(s) to ${#ENGINES[@]} engines..."

PAYLOAD=$(jq -n \
  --arg host "$HOST" \
  --arg key "$KEY" \
  --arg keyLocation "$KEY_LOCATION" \
  --argjson urlList "$(printf '%s\n' "${URLS[@]}" | jq -R . | jq -s .)" \
  '{host: $host, key: $key, keyLocation: $keyLocation, urlList: $urlList}')

for ENGINE in "${ENGINES[@]}"; do
  echo ""
  echo "→ $ENGINE"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$ENGINE" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
  echo "  Status: $HTTP_CODE"
done

echo ""
echo "Done."
