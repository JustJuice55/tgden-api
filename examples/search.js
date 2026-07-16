#!/usr/bin/env node
// Search the tgden Telegram catalog. No API key needed. Node 18+ (built-in fetch).
// Usage: node search.js "crypto"

const BASE = "https://tgden.com";

async function search(query, { limit = 5, type } = {}) {
  const p = new URLSearchParams({ q: query, limit: String(limit) });
  if (type) p.set("type", type);
  const res = await fetch(`${BASE}/api/catalog?${p}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()).items ?? [];
}

const q = process.argv[2] || "crypto";
for (const it of await search(q)) {
  console.log(`@${(it.username || "—").padEnd(20)} ${it.title || ""}`);
}
