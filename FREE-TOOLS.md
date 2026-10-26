# Free Telegram tools

Choose a tool, provide its input, download JSON and CSV. Run locally or use your own public GitHub fork as a small task runner.

## Local use

```bash
git clone https://github.com/JustJuice55/tgden-api.git
cd tgden-api
python3 -m tgden_tools --help
```

There are no third-party Python dependencies and no account or key setup. The release also provides a `tgden-tools.pyz` download, which runs with Python 3.10+ without cloning the repository:

```bash
python3 tgden-tools.pyz groups --query python --limit 10 --output output
```

## Examples

```bash
# Search public groups, channels and bots.
python3 -m tgden_tools groups --query "python" --limit 20 --output groups
python3 -m tgden_tools channels --query "artificial intelligence" --limit 10 --output channels
python3 -m tgden_tools bots --query "moderation" --limit 10 --output bots

# Look up exact public usernames in the catalog.
python3 -m tgden_tools lookup --username "telegram,durov,botfather" --output lookup

# Export public marketplace-listing metadata.
python3 -m tgden_tools classifieds --country th --limit 10 --output ads

# Get a small masked buyer-request preview from the existing public endpoint.
python3 -m tgden_tools buyer-preview --country vn --category real-estate --days 30 --limit 3 --output buyers

# Search captured channel-post snippets.
python3 -m tgden_tools post-search --query "OpenAI" --limit 10 --output matches

# Read the channel's current public web preview directly from Telegram.
python3 -m tgden_tools channel-posts --username telegram --limit 5 --output posts
```

`groups`, `channels` and `bots` use keyword search. Their results are catalog matches, not a check of current responsiveness or a semantic match guarantee. `lookup` reports exact catalog matches; a missing catalog record does not mean a username is available to register.

`channel-posts` reads the public `t.me/s/…` page directly. It returns the posts in that page, often around 20. Private groups, invitation links and a full historical crawl are not supported. No bot is started and no group is joined.

`buyer-preview` uses the same masked public preview available on TGDen. It is limited to 10 rows and the endpoint's existing rate limit. It does not export sender identities or contact details. The full partner product includes capabilities outside this free sample.

The marketplace tool exports existing listing metadata and original source links. Asking prices are not transactions or comparable market medians. The free tools do not calculate price statistics.

## Run on GitHub

1. [Fork the public repository](https://github.com/JustJuice55/tgden-api/fork).
2. Open **Actions** in your fork and enable workflows if prompted.
3. Select **Run Telegram Tool**, then **Run workflow**.
4. Select a tool and fill only the relevant inputs: query, username, country, category, result limit and days.
5. Open the completed run and download its result artifact.

The artifact contains:

- `result.json` — result envelope, rows and source information;
- `result.csv` — the result rows;
- `metadata.json` — run details and limits.

Source failures cause a failed run. They are not converted into a successful empty dataset. A valid search with no matches can successfully return zero rows.

The workflow uses a standard Linux runner, a five-minute time limit and read-only repository permissions. Standard hosted runner execution is free in public repositories under [GitHub's current billing rules](https://docs.github.com/en/billing/concepts/product-billing/github-actions). Artifacts are retained for one day; GitHub's storage and account limits still apply. [Downloading an artifact requires signing in](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

Inputs, logs and artifacts in a public workflow can be visible to other people. Use public search terms and public channel names. Local use is available when you do not want to publish a query or result through GitHub.

## Sources and limits

| Tool | Request surface | Run limit |
| --- | --- | --- |
| groups / channels / bots | Public catalog keyword search | Up to 50 requested matches |
| lookup | Exact-handle public catalog searches | Up to 10 usernames |
| classifieds | Public marketplace listings | Up to 50 requested rows |
| buyer-preview | Public masked demand preview | Up to 10 rows; source rate limit applies |
| post-search | Captured public channel snippets | Up to 50 requested matches |
| channel-posts | One public Telegram preview page | Only the posts present in that page |

The keyword search tools do not accept a country filter. Country and category inputs are intended for marketplace and buyer-preview modes. Unsupported input is rejected rather than silently ignored.

TGDen-backed tools depend on the availability and coverage of the public TGDen service. The direct channel-preview exporter is independent of that catalog. No Apify service is called by this bundle.

Output links to TGDen contain public campaign parameters so incoming visits can be distinguished from this tool. They contain no personal tracking identifier. Direct Telegram and original-source links remain available.

## License

The tool code is [MIT licensed](LICENSE). Linked Telegram content and third-party names retain their own rights. A result is an observation from its stated source, not an endorsement of a group, bot, listing or buyer.
