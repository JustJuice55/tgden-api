"""CLI: python3 -m tgden_tools TOOL [options]."""
import argparse
import sys
from . import TOOLS, SourceError, run_tool
from .export import write_results


def parser():
    result = argparse.ArgumentParser(description="Free, bounded public Telegram tools. No account or API key.")
    result.add_argument("tool", choices=TOOLS)
    result.add_argument("--query", default="", help="Keyword query, 1–200 characters")
    result.add_argument("--username", default="", help="Public @handle or https://t.me/handle; lookup accepts up to 10 comma-separated")
    result.add_argument("--country", default="", help="Two-letter country code for classifieds or buyer-preview")
    result.add_argument("--category", default="", help="Public category slug for classifieds or buyer-preview")
    result.add_argument("--limit", type=int, default=10, help="1–50; lookup/buyer-preview max 10; channel-posts max 20")
    result.add_argument("--days", type=int, default=7, help="1–30 for buyer-preview only")
    result.add_argument("--output", default="output", help="Directory for result.json, result.csv and metadata.json")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    values = vars(args).copy()
    output = values.pop("output")
    tool = values.pop("tool")
    try:
        result = run_tool(tool, **values)
        target = write_results(result, output)
    except (SourceError, ValueError, OSError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    print("%s: %s result(s). Source: %s. Files: %s" % (tool, result["count"], result["source"], target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
