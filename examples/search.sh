#!/usr/bin/env bash
# Search the tgden Telegram catalog. No API key needed.
# Usage: ./search.sh "crypto"
set -euo pipefail
Q="${1:-crypto}"
curl -s "https://tgden.com/api/catalog?q=$(printf %s "$Q" | jq -sRr @uri)&limit=5" \
  | jq -r '.items[] | "@\(.username // "—")  \(.title)"'
