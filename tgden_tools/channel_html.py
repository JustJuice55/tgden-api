"""Read text from one public Telegram preview page, without media requests."""
from html.parser import HTMLParser
import re
from .network import MAX_BYTES, SourceError

_POST = re.compile(r"([A-Za-z0-9_]{3,32})/([1-9][0-9]{0,18})\Z")
_VOID = {"br", "hr", "img", "meta", "link", "input", "source", "wbr", "area", "base", "col", "embed", "param", "track"}


class ChannelParser(HTMLParser):
    def __init__(self, username):
        super().__init__(convert_charrefs=True)
        self.username = username
        self.stack = []
        self.current = None
        self.items = []
        self.has_history = False
        self.closed_history = False

    def active(self, key):
        return any(frame[key] for frame in self.stack)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if "tgme_channel_history" in classes:
            self.has_history = True
        if "tgme_widget_message" in classes:
            match = _POST.fullmatch(attrs.get("data-post", ""))
            if (not self.active("history") or self.current is not None or not match
                    or match[1].lower() != self.username):
                raise SourceError("Public preview contains an invalid channel post")
            self.current = {"depth": len(self.stack), "parts": [], "views_parts": [],
                            "channel": self.username,
                            "message_url": "https://t.me/%s/%s" % (self.username, match[2]),
                            "posted_at": None}
        if self.current is not None and not self.active("skip"):
            if tag == "br" and self.active("text"):
                self.current["parts"].append("\n")
            elif tag in {"p", "div", "blockquote", "pre"} and self.active("text"):
                self.current["parts"].append("\n")
            if tag == "time" and attrs.get("datetime"):
                self.current["posted_at"] = attrs["datetime"]
        if tag not in _VOID:
            self.stack.append({"tag": tag, "text": "tgme_widget_message_text" in classes,
                               "views": "tgme_widget_message_views" in classes,
                               "skip": tag in {"script", "style", "template"},
                               "history": "tgme_channel_history" in classes})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.current is None or self.active("skip"):
            return
        if self.active("text"):
            self.current["parts"].append(data)
        if self.active("views"):
            self.current["views_parts"].append(data)

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack) - 1, -1, -1)
                      if self.stack[i]["tag"] == tag), None)
        if index is None:
            return
        if self.current is not None and self.active("text") and not self.active("skip") and tag in {"p", "div", "blockquote", "pre"}:
            self.current["parts"].append("\n")
        if any(frame["history"] for frame in self.stack[index:]):
            self.closed_history = True
        del self.stack[index:]
        if self.current is not None and len(self.stack) <= self.current["depth"]:
            post = self.current
            self.items.append({"channel": post["channel"], "message_url": post["message_url"],
                               "text": "".join(post["parts"]).strip(),
                               "posted_at": post["posted_at"],
                               "views": "".join(post["views_parts"]).strip() or None})
            self.current = None


def parse_channel_page(body, username, limit):
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BYTES:
        raise SourceError("Expected a public HTML preview of at most 2 MiB")
    parser = ChannelParser(username)
    try:
        parser.feed(body)
        parser.close()
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError("Could not parse the public channel preview") from exc
    if not parser.has_history or not parser.closed_history or parser.current is not None:
        raise SourceError("No complete public channel feed found; private, contact, challenge and unsupported pages cannot be exported")
    return parser.items[-limit:]
