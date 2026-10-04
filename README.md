# technews-widget

A small always-handy window with 1-3 line summaries of the latest big-tech news: Anthropic, Apple, OpenAI, Google, Microsoft, Nvidia, Meta, Amazon, Tesla.

- **No API key.** Headlines come from Google News RSS (US, UK and Hong Kong editions), de-duplicated and filtered. Summaries are written by `claude -p --model haiku`, so it uses your existing Claude Code login.
- **Headline-only summaries**, so a summary never claims more than the headline does.
- **Stale-safe.** If a fetch fails, the last good stories stay on screen with a "stale" note.
- Opens as a small Chrome app window with its own profile, so your normal Chrome is untouched.

## Requirements

macOS, Google Chrome, Python 3.9+, and the [Claude Code](https://claude.com/claude-code) CLI logged in.

## Run it

```bash
python3 01-app/serve.py &      # serves http://127.0.0.1:8765 and refreshes every 30 min
./01-app/open-window.sh        # opens the window
```

## Open automatically at login

```bash
./03-launchd/install.sh        # undo with ./03-launchd/uninstall.sh
```

Clone this into a folder like `~/.local/share`, not `~/Desktop`, `~/Documents` or `~/Downloads`: macOS blocks launchd jobs from running scripts stored there.

## Customise

Edit `01-app/config.json`: add a company (`name`, a Google News `query`, and `must` words that a headline has to contain), or change `stories_per_company`, `max_age_hours`, `refresh_minutes`, `port`, `block_words` and `editions`. Press Refresh in the window.

## Layout

| Path | What |
|---|---|
| `01-app/fetch.py` | Pull RSS, filter, summarise, write the page |
| `01-app/serve.py` | Local server plus periodic refresh |
| `01-app/open-window.sh` | Open the Chrome app window (retries at login) |
| `03-launchd/` | Login auto-start install and uninstall |
| `02-data/` | Created at runtime, git-ignored |

MIT licensed.
