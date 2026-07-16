# Telegram Search API — free, public, no key required

A free HTTP API to **search Telegram** — channels, group chats, and bots — across a
public catalog of **875,000+** entities. No signup, no API key, no OAuth. Just `GET`.

Powered by [**tgden.com**](https://tgden.com) — a search engine and catalog for the
open Telegram web (`t.me/s/…`). We index only public links; no content is hosted here.

> Looking for the human UI? → **https://tgden.com** · Interactive docs → **https://tgden.com/en/api-docs**

---

## Why this exists

Telegram has no official public search. Finding a channel, a live discussion group, or
a bot by topic means guessing usernames or trusting closed directories. tgden indexes the
public Telegram web and exposes it as a clean JSON API that anyone — developers, LLM agents,
researchers — can query for free. This repo is the developer front door: endpoints, examples,
and limits, all in one place.

## Endpoints

Base URL: `https://tgden.com`

### `GET /api/catalog` — search the catalog

| Param   | Type   | Default | Notes                                             |
|---------|--------|---------|---------------------------------------------------|
| `q`     | string | —       | Free-text query (title, username, topic)          |
| `limit` | int    | `20`    | Max results to return                             |
| `type`  | string | all     | `channel` · `chat` · `bot` (omit for everything)  |

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

### `GET /api/suggest` — instant autocomplete

Grouped, ranked suggestions as-you-type. Great for search boxes and agent tool-use.

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

## Limits (published, honest)

- **No API key, no hard per-key quota today.** Be reasonable — this is a shared free service.
- A shared IP rate limit protects the origin (~200 requests / 10s per IP). Verified search-engine
  and AI crawlers are excluded.
- Need higher, guaranteed throughput or bulk export? Open an issue or reach us via
  [@tgden_bot](https://t.me/tgden_bot) — we're happy to work with real projects.

We treat these limits as a contract: when they change, we announce it here and in
[the docs](https://tgden.com/en/api-docs). No silent throttling.

## Quick start

- [`examples/search.sh`](examples/search.sh) — curl one-liner
- [`examples/search.py`](examples/search.py) — Python (stdlib only)
- [`examples/search.js`](examples/search.js) — Node.js (fetch)

## Use cases

- **LLM / agent tool-use** — give your agent a `telegram_search(query)` tool in one HTTP call.
- **Discovery bots** — recommend channels/chats by topic.
- **Research** — map communities, track niches, study the open Telegram graph.

## License

[MIT](LICENSE) — do what you want, no warranty. Data is public Telegram metadata.

---

<sub>Maintained by [tgden.com](https://tgden.com). Not affiliated with Telegram FZ-LLC.
Indexes public `t.me` links only.</sub>
