# tgden — Telegram catalog as an MCP server + free API

**A live index of what exists *on* Telegram: 1.2M+ channels, 245k+ group chats, 160k+ bots,
4.9M+ indexed posts.** No Telegram account. No API key. No install. CORS enabled — it runs
from a browser tab as happily as from a server.

- **MCP endpoint** — `https://tgden.com/api/mcp`
- **REST API** — `https://tgden.com/api/catalog`
- **Human UI** — [tgden.com](https://tgden.com) · **Docs** — [tgden.com/en/api-docs](https://tgden.com/en/api-docs)

---

## Why another Telegram MCP server?

Every other Telegram MCP server connects to **your** Telegram account — you hand it an API
hash, a phone number or a bot token, and it reads *your* dialogs, sends *your* messages,
manages *your* groups. Useful, but it can only ever see what you already have access to.

This one is the opposite. It's a **public catalog**, so it answers the question none of the
others can:

> *"What Telegram channels and groups exist about X, and which are worth joining?"*

|                            | account-based Telegram MCP        | **tgden MCP**                         |
| -------------------------- | --------------------------------- | ------------------------------------- |
| Credentials required       | API ID/hash, phone or bot token   | **none**                              |
| Install                    | local process (Python/Go/Node)    | **none — a hosted HTTP URL**          |
| Can see                    | chats you already joined          | **1.6M+ public entities you haven't** |
| Answers *"what exists?"*   | no                                | **yes**                               |
| Can act on your account    | yes                               | no — **read-only by design**          |

Because it never touches an account, there's nothing to leak and nothing to get banned.

---

## Quick start

**Claude Code**

```bash
claude mcp add --transport http tgden https://tgden.com/api/mcp
```

**Claude Desktop · Cursor · any MCP client** — add to your MCP config:

```json
{
  "mcpServers": {
    "tgden": {
      "type": "http",
      "url": "https://tgden.com/api/mcp"
    }
  }
}
```

That's the entire setup: streamable HTTP transport, stateless, no auth handshake.

**Check it by hand:**

```bash
curl -s https://tgden.com/api/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[].name'
```

### Tools

| Tool | What it answers |
| ---- | --------------- |
| `search_telegram` | Full-text search across channels, group chats and bots — with subscriber/member counts, categories and trust scores. |
| `best_channels_by_category` | *"Best Telegram channels for crypto / AI / news / gaming…"* — ranked by subscribers. |
| `channel_stats` | Everything known about one channel, by `@username`. |
| `search_posts` | Full-text search over recent posts — what channels actually **said**, not just their bio. |
| `market_listings` | Real classified listings (rent, sale, services, jobs) parsed from regional Telegram groups across 🇦🇪 🇹🇷 🇹🇭 🇻🇳 🇬🇪 🇺🇸. |
| `market_stats` | Listing totals by country and type. |

### Resources

| URI | Contents |
| --- | -------- |
| `tgden://catalog/top-channels` | Top-100 channels by subscribers. |
| `tgden://catalog/categories` | Full category taxonomy with channel counts. |
| `tgden://market/listings-latest` | The 100 freshest marketplace listings. |
| `tgden://market/stats` | Marketplace totals by country and type. |

---

## Free REST API (no key either)

Telegram has no official public search. Finding a channel, a live discussion group or a bot
by topic means guessing usernames or trusting closed directories. If you don't speak MCP,
the same catalog is plain HTTP.

### `GET /api/catalog` — search

| Param   | Type   | Default | Notes                                            |
|---------|--------|---------|--------------------------------------------------|
| `q`     | string | —       | Free-text query (title, username, topic)         |
| `limit` | int    | `20`    | Max results to return                            |
| `type`  | string | all     | `channel` · `chat` · `bot` (omit for everything) |

```bash
curl "https://tgden.com/api/catalog?q=crypto&type=channel&limit=3"
```

```json
{
  "items": [
    {
      "id": "6ec0407a-4f5e-4a86-9154-f42481bc9413",
      "telegram_id": 2075341442,
      "username": "hamster_kombat",
      "title": "Hamster Kombat Announcement",
      "is_private": false,
      "avatar_url": "https://cdn4.telesco.pe/file/…"
    }
  ]
}
```

### Call it from the browser

`Access-Control-Allow-Origin: *` is set on both read-only endpoints, so there is no proxy
step: paste this into any page's devtools console (or a CodePen) and it answers.

```js
const r = await fetch("https://tgden.com/api/catalog?q=crypto&type=channel&limit=3");
console.table((await r.json()).items);
```

Rate limit is shared and fair-use (~200 requests / 10s per IP). No key, no signup, no CORS
proxy, no `Access-Control-Allow-Credentials` — nothing of yours is ever sent.

### `GET /api/suggest` — instant autocomplete

Grouped, ranked suggestions as-you-type. Good for search boxes and agent tool-use.

```bash
curl "https://tgden.com/api/suggest?q=btc"
```

```json
{
  "groups": [
    {
      "key": "chats",
      "label": { "en": "live chats", "ru": "живые чаты" },
      "items": [
        { "label": "BTC Times Discussion", "sub": "221 members",
          "href": "/en/chat/thebtctimes", "kind": "chat", "username": "thebtctimes" }
      ]
    }
  ]
}
```

Runnable examples: [shell](examples/search.sh) · [Python](examples/search.py) · [JavaScript](examples/search.js).

---

## Limits — published, because hidden limits are worse than low ones

| Surface | Limit |
| ------- | ----- |
| REST (`/api/catalog`, `/api/suggest`) | ~200 requests / 10s per IP, shared fair-use |
| MCP (`/api/mcp`) | 240 calls / hour per IP |
| Auth | none — no key, no signup, no email |
| Cost | free |

Verified search-engine and AI crawlers are excluded from the shared limit.

We treat these as a contract: when they change, we announce it here and in
[the docs](https://tgden.com/en/api-docs). **No silent throttling.** Need guaranteed
throughput or a bulk export for something real? Open an issue, or reach us via
[@tgden_bot](https://t.me/tgden_bot).

---

## About the data

Parsed continuously from Telegram's public surfaces — **fresher than any LLM training set**,
which is most of the point of exposing it over MCP.

| | |
| --- | --- |
| Channels | 1,298,868 |
| Group chats | 282,719 |
| Bots | 157,909 |
| Indexed posts | 4,955,162 |
| Marketplace listings | 34,862 |

*Census 06.08.2026. The MCP server reports these totals **live**, so what your agent sees is
current — not whatever was true when this file was written.*

Public data only: channels, groups and bots that are already publicly listed or linked.
No private groups, no archives from closed communities, no personal data.

---

## Use cases

- **Agent tool-use** — give an agent real Telegram discovery in one config line.
- **Research** — map communities, track niches, study the open Telegram graph.
- **Discovery bots** — recommend channels and chats by topic.
- **Market intel** — what's being rented, sold and offered in regional Telegram economies.

Machine-readable site summary for AI crawlers: <https://tgden.com/llms.txt>

## License

[MIT](LICENSE) — do what you want, no warranty. Data is public Telegram metadata.

---

<sub>Maintained by [tgden.com](https://tgden.com). Not affiliated with Telegram FZ-LLC.
Indexes public `t.me` links only.</sub>
