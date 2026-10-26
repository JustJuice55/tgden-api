#!/usr/bin/env python3
"""Run manual GitHub inputs as data; never shell commands or filesystem paths."""
import html
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tgden_tools import SourceError, run_tool  # noqa: E402
from tgden_tools.export import write_results  # noqa: E402


def summary(result):
    lines = ["## Free Telegram tool result", "",
             "- Tool: **%s**" % html.escape(result["tool"]),
             "- Exported rows: **%s**" % result["count"],
             "- Source: %s" % html.escape(result["source"]),
             "- %s" % html.escape(result["scope"]), "",
             "[TGDen public catalog](https://tgden.com/?utm_source=github&utm_medium=free_tools&utm_campaign=telegram_tools)"]
    source_url = result.get("source_url")
    if source_url:
        # These URLs are constructed by the adapters; query strings are percent-encoded.
        lines.append("[Public source used](%s)" % source_url)
    links = []
    for item in result["items"][:5]:
        for field in ("catalog_url", "market_url", "message_url", "source_message_url", "tme_url", "tg_link"):
            if item.get(field):
                links.append("- [Result %s](%s)" % (len(links) + 1, item[field]))
                break
    if links:
        lines.extend(["", "A few exported public links:", ""] + links)
    lines.extend(["", "Download the JSON, CSV and metadata in the run's artifact (GitHub sign-in required). Artifacts expire after one day.", ""])
    return "\n".join(lines)


def main(environ=None):
    environ = os.environ if environ is None else environ
    try:
        result = run_tool(environ.get("TG_TOOL", ""),
                          query=environ.get("TG_QUERY", ""), username=environ.get("TG_USERNAME", ""),
                          country=environ.get("TG_COUNTRY", ""), category=environ.get("TG_CATEGORY", ""),
                          limit=int(environ.get("TG_LIMIT", "10")), days=int(environ.get("TG_DAYS", "7")))
        write_results(result, ROOT / "output")
        # GITHUB_STEP_SUMMARY is supplied by the runner, never a workflow input.
        if environ.get("GITHUB_STEP_SUMMARY"):
            with open(environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write(summary(result))
    except (SourceError, ValueError, OSError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    print("%s: exported %s row(s) from %s" % (result["tool"], result["count"], result["source"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
