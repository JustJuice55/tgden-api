"""Small public-only HTTP reader: no credentials, pagination or automatic retries."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "TGDen-Free-Tools/1.0 (+https://github.com/JustJuice55/tgden-api)"


class SourceError(RuntimeError):
    """The public source did not return a usable response."""


def validate_source_url(url, host):
    try:
        parts = urllib.parse.urlsplit(url)
        valid = (parts.scheme == "https" and parts.netloc == host and
                 parts.hostname == host and parts.username is None and
                 parts.password is None and parts.port is None and not parts.fragment)
    except ValueError as exc:
        raise SourceError("Invalid public source URL") from exc
    if not valid:
        raise SourceError("Only HTTPS on the exact public source host is allowed")
    return parts


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def __init__(self, host):
        self.host = host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_source_url(newurl, self.host)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PublicClient:
    """At most ten reads, fifteen seconds per read, sixty seconds total."""

    def __init__(self):
        self.started = time.monotonic()
        self.calls = 0

    def read(self, url, host):
        validate_source_url(url, host)
        remaining = 60 - (time.monotonic() - self.started)
        if self.calls >= 10 or remaining <= 0:
            raise SourceError("Free tool request/time budget exceeded")
        self.calls += 1
        opener = urllib.request.build_opener(PublicRedirectHandler(host))
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json" if host == "tgden.com" else "text/html",
            "Accept-Encoding": "identity",
        })
        try:
            with opener.open(request, timeout=min(15, remaining)) as response:
                validate_source_url(response.geturl(), host)
                if response.status != 200:
                    raise SourceError("Public source returned HTTP %s" % response.status)
                length = response.headers.get("Content-Length")
                if length and int(length) > MAX_BYTES:
                    raise SourceError("Public response exceeds the 2 MiB free limit")
                chunks = []
                size = 0
                while True:
                    if time.monotonic() - self.started >= 60:
                        raise SourceError("Free tool time budget exceeded")
                    chunk = response.read(min(65536, MAX_BYTES + 1 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise SourceError("Public response exceeds the 2 MiB free limit")
                    chunks.append(chunk)
                return b"".join(chunks)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise SourceError("Public source rate limit reached (HTTP 429); try later. No retries performed.") from exc
            raise SourceError("Public source returned HTTP %s" % exc.code) from exc
        except SourceError:
            raise
        except (OSError, ValueError) as exc:
            raise SourceError("Could not read the public source: %s" % type(exc).__name__) from exc

    def fetch_json(self, url):
        try:
            return json.loads(self.read(url, "tgden.com").decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise SourceError("Public source did not return valid JSON") from exc

    def fetch_text(self, url):
        return self.read(url, "t.me").decode("utf-8", errors="replace")
