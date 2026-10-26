"""Explicit public endpoint adapters and field projections for eight free modes."""
from datetime import datetime, timezone
import re
from urllib.parse import urlencode, urlsplit
from .channel_html import parse_channel_page
from .network import PublicClient, SourceError

TOOLS = ("groups", "channels", "bots", "lookup", "classifieds", "buyer-preview", "post-search", "channel-posts")
_USERNAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,31}\Z", re.ASCII)
_COUNTRY = re.compile(r"[a-z]{2}\Z", re.ASCII)
_CATEGORY = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z", re.ASCII)
_TRACKING = "utm_source=github&utm_medium=free_tools&utm_campaign=telegram_tools"


def normalize_username(value):
    """Accept one public handle or exact t.me/name or t.me/s/name URL."""
    if not isinstance(value, str):
        raise ValueError("A public Telegram username is required")
    value = value.strip()
    if value.startswith("https://"):
        try:
            parts = urlsplit(value)
            if (parts.netloc != "t.me" or parts.hostname != "t.me" or
                    parts.username is not None or parts.password is not None or
                    parts.port is not None or parts.query or parts.fragment):
                raise ValueError("Use an HTTPS t.me public username URL without parameters")
            path = parts.path.strip("/")
            value = path[2:] if path.startswith("s/") else path
        except ValueError as exc:
            raise ValueError("Use a public https://t.me/username URL") from exc
    elif value.startswith("@"):
        value = value[1:]
    if not _USERNAME.fullmatch(value):
        raise ValueError("Public usernames must be 3–32 ASCII letters, digits or underscores and start with a letter; private invites are unsupported")
    return value.lower()


def _text(value, label, maximum=200):
    if not isinstance(value, str):
        raise ValueError("%s must be text" % label)
    value = value.strip()
    if len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError("%s must be at most %s characters without control characters" % (label, maximum))
    return value


def _integer(value, label, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError("%s must be an integer between 1 and %s" % (label, maximum))
    return value


def _rows(data, key):
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise SourceError("Public source schema changed: expected a %s array" % key)
    if any(not isinstance(row, dict) for row in data[key]):
        raise SourceError("Public source schema changed: expected object rows")
    return data[key]


def _catalog_rows(data):
    rows = _rows(data, "items")
    if any(row.get("entity_type") not in ("chat", "channel", "bot") for row in rows):
        raise SourceError("Public catalog schema changed: expected an entity_type for every row")
    return rows


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _copy_text(row, keys):
    return {key: row[key] for key in keys if isinstance(row.get(key), str)}


def _public_handle(row, key="username"):
    if row.get("is_private") not in (None, False) or row.get("private") not in (None, False):
        return None
    value = row.get(key)
    if not isinstance(value, str) or not _USERNAME.fullmatch(value):
        return None
    return value.lower()


def _catalog_row(row, expected=None):
    username = _public_handle(row)
    kind = row.get("entity_type")
    if username is None or kind not in {"chat", "channel", "bot"} or (expected and kind != expected):
        return None
    item = {"username": username, "entity_type": kind}
    item.update(_copy_text(row, ("title", "language")))
    if isinstance(row.get("language"), list):
        item["language"] = [language for language in row["language"] if isinstance(language, str)]
    for key in ("members_count", "subscribers_count", "posts_count", "views_count"):
        if _count(row.get(key)):
            item[key] = row[key]
    if isinstance(row.get("verified"), bool):
        item["verified"] = row["verified"]
    if isinstance(row.get("categories"), list):
        item["categories"] = [c for c in row["categories"] if isinstance(c, str)]
    item["telegram_url"] = "https://t.me/" + username
    if kind == "bot":
        item["catalog_url"] = "https://tgden.com/en/bots?%s&%s" % (urlencode({"q": username}), _TRACKING)
    else:
        item["catalog_url"] = "https://tgden.com/en/%s/%s?%s" % (kind, username, _TRACKING)
    return item


def _message_url(username, message_id):
    if isinstance(message_id, bool):
        return None
    if isinstance(message_id, int) and 0 < message_id <= 10 ** 19:
        return "https://t.me/%s/%s" % (username, message_id)
    if isinstance(message_id, str) and re.fullmatch(r"[1-9][0-9]{0,18}", message_id):
        return "https://t.me/%s/%s" % (username, message_id)
    return None


def _preview_link(row, username):
    link = row.get("tg_link")
    if not isinstance(link, str):
        return None
    match = re.fullmatch(r"https://t\.me/([A-Za-z][A-Za-z0-9_]{2,31})/([1-9][0-9]{0,18})", link)
    if match and match[1].lower() == username:
        return _message_url(username, match[2])
    return None


def _call(fetcher, url):
    try:
        return fetcher(url)
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError("Public source request failed (%s); no successful result was produced" % type(exc).__name__) from exc


def run_tool(tool, *, query='', username='', country='', category='', limit=10, days=7, fetch_json=None, fetch_text=None):
    """Run one bounded read. Injected fetchers accept a URL only, for offline use."""
    if tool not in TOOLS:
        raise ValueError("Unknown tool; choose: " + ", ".join(TOOLS))
    query = _text(query, "query")
    username = _text(username, "username", 1000)
    country = _text(country, "country", 2).lower()
    category = _text(category, "category", 64).lower()
    _integer(days, "days", 30)
    maximum = 10 if tool in {"lookup", "buyer-preview"} else 20 if tool == "channel-posts" else 50
    _integer(limit, "limit", maximum)
    if country and not _COUNTRY.fullmatch(country):
        raise ValueError("country must be a two-letter code, for example vn or th")
    if category and not _CATEGORY.fullmatch(category):
        raise ValueError("category must be a public category slug, for example real-estate")
    if tool not in {"classifieds", "buyer-preview"} and (country or category):
        raise ValueError("country/category filters are supported only by classifieds and buyer-preview")
    if tool not in {"lookup", "channel-posts"} and username:
        raise ValueError("username is supported only by lookup and channel-posts")
    if tool in {"lookup", "channel-posts"} and query:
        raise ValueError("Use username for this mode; query is unsupported")
    if tool in {"groups", "channels", "bots", "post-search"} and not query:
        raise ValueError("query must contain 1–200 characters")
    if tool == "classifieds" and query:
        raise ValueError("This classifieds mode accepts country/category and does not support keyword query")
    if tool == "buyer-preview" and not (query or country or category):
        raise ValueError("buyer-preview requires a query, country or category")
    if days != 7 and tool != "buyer-preview":
        raise ValueError("days is supported only by buyer-preview")

    client = PublicClient()
    get_json = fetch_json if fetch_json is not None else client.fetch_json
    get_text = fetch_text if fetch_text is not None else client.fetch_text
    result = {"tool": tool, "items": [], "count": 0,
              "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "limits": {"max_items": maximum, "requested_items": limit, "max_requests": 10 if tool == "lookup" else 1,
                         "pagination": False, "auth_required": False}}

    def api(path, params):
        url = "https://tgden.com/api/v1/" + path + "?" + urlencode(params)
        result["source_url"] = url
        return _call(get_json, url)

    if tool in {"groups", "channels", "bots"}:
        kind = {"groups": "chat", "channels": "channel", "bots": "bot"}[tool]
        data = api("search", {"q": query, "type": kind, "limit": limit})
        result["items"] = [item for row in _catalog_rows(data)[:limit] if (item := _catalog_row(row, kind)) is not None]
        result["source"] = "TGDen public catalog keyword search"
        result["scope"] = "Catalog metadata; matches and verified flags do not prove live availability or safety."
    elif tool == "lookup":
        if not username:
            raise ValueError("lookup requires one to ten comma-separated public usernames")
        names = list(dict.fromkeys(normalize_username(part) for part in username.split(",")))
        if len(names) > 10:
            raise ValueError("lookup accepts at most ten public usernames per run")
        if len(names) > limit:
            raise ValueError("lookup limit must be at least the number of unique usernames")
        for name in names:
            data = api("search", {"q": name, "type": "all", "limit": 50})
            matches = [item for row in _catalog_rows(data)[:50] if (item := _catalog_row(row)) is not None and item["username"] == name]
            if matches:
                item = matches[0]
                item["lookup_status"] = "catalog_match"
            else:
                item = {"username": name, "lookup_status": "not_found", "telegram_url": "https://t.me/" + name}
            result["items"].append(item)
        result.pop("source_url", None)
        result["source"] = "TGDen public catalog exact-handle lookup"
        result["scope"] = "not_found means absent from this successful catalog search, not a claim about Telegram account availability."
    elif tool == "classifieds":
        params = {"limit": limit}
        params.update({k: v for k, v in (("country", country), ("category", category)) if v})
        data = api("market/listings", params)
        for row in _rows(data, "items")[:limit]:
            item = _copy_text(row, ("country", "type", "direction", "category", "title", "price_currency", "location", "lang", "status", "posted_at", "created_at"))
            listing_id = row.get("id")
            if isinstance(listing_id, (str, int)) and not isinstance(listing_id, bool) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", str(listing_id)):
                item["id"] = listing_id
                item["market_url"] = "https://tgden.com/en/market/%s?%s" % (listing_id, _TRACKING)
            if isinstance(row.get("price_amount"), (str, int, float)) and not isinstance(row.get("price_amount"), bool):
                item["price_amount"] = row["price_amount"]
            if isinstance(row.get("suspicious"), bool):
                item["suspicious"] = row["suspicious"]
            handle = _public_handle(row, "source_chat_username")
            link = _message_url(handle, row.get("source_msg_id")) if handle else None
            if link:
                item["source_message_url"] = link
            result["items"].append(item)
        result["source"] = "TGDen public marketplace listings"
        result["scope"] = "One public listings page; prices are source listing values, not estimates or comparable medians."
    elif tool == "buyer-preview":
        params = {"days": days, "limit": limit}
        params.update({k: v for k, v in (("q", query), ("country", country), ("category", category)) if v})
        data = api("intent/preview", params)
        for row in _rows(data, "preview")[:limit]:
            handle = _public_handle(row, "chat_username")
            if not handle:
                continue
            item = {"chat_username": handle}
            item.update(_copy_text(row, ("chat_title", "snippet", "posted_at", "category", "country", "intent")))
            if _count(row.get("posted_at_ts")):
                item["posted_at_ts"] = row["posted_at_ts"]
            if isinstance(row.get("has_contact"), bool):
                item["has_contact"] = row["has_contact"]
            link = _preview_link(row, handle)
            if link:
                item["tg_link"] = link
            result["items"].append(item)
        if "more" in data and not isinstance(data["more"], bool):
            raise SourceError("Public preview schema changed: more must be boolean")
        result["more"] = data.get("more", False)
        result["limits"].update({"public_rate_limit": "60 requests/hour/IP", "max_days": 30})
        result["source"] = "TGDen public masked buyer-intent preview"
        result["scope"] = "Limited masked preview; no author/contact identities or paid semantic/group-demand parity."
    elif tool == "post-search":
        data = api("posts/search", {"q": query, "kind": "channel", "limit": limit, "min_views": 0})
        for row in _rows(data, "items")[:limit]:
            handle = _public_handle(row, "channel_username")
            link = _message_url(handle, row.get("telegram_msg_id")) if handle else None
            if not link:
                continue
            item = {"channel_username": handle, "telegram_msg_id": row["telegram_msg_id"], "tme_url": link}
            item.update(_copy_text(row, ("snippet", "posted_at")))
            if _count(row.get("views")):
                item["views"] = row["views"]
            result["items"].append(item)
        result["source"] = "TGDen public indexed channel-post search"
        result["scope"] = "Snippets from TGDen's channel index, not a search of all Telegram or complete post history."
    else:
        handle = normalize_username(username)
        url = "https://t.me/s/" + handle
        result["items"] = parse_channel_page(_call(get_text, url), handle, limit)
        result["source"] = "Telegram public channel web preview"
        result["source_url"] = url
        result["limits"].update({"preview_pages": 1, "max_response_bytes": 2097152, "media_downloads": False})
        result["scope"] = "Latest text visible on one public preview page, usually up to 20 posts; no complete history or private access."

    result["count"] = len(result["items"])
    if tool not in {"channel-posts", "lookup"} and isinstance(data, dict) and _count(data.get("total")):
        result["source_total"] = data["total"]
    return result
