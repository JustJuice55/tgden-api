#!/usr/bin/env python3
"""Search the tgden Telegram catalog. No API key needed. Stdlib only.

Usage: python search.py "crypto"
"""
import json
import sys
import urllib.parse
import urllib.request

BASE = "https://tgden.com"


def search(query: str, limit: int = 5, kind: str | None = None) -> list[dict]:
    params = {"q": query, "limit": limit}
    if kind:
        params["type"] = kind
    url = f"{BASE}/api/catalog?" + urllib.parse.urlencode(params)
    # Always send a real User-Agent — the CDN rejects the default library UA.
    req = urllib.request.Request(url, headers={"User-Agent": "tgden-api-example/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp).get("items", [])


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "crypto"
    for it in search(q):
        print(f"@{it.get('username') or '—':<20} {it.get('title', '')}")
