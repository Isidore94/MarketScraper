# MarketScraper

Scripts for collecting market-related information from a handful of public
sources and compiling the results into a single Markdown briefing.  The
project is organised into small, composable modules so you can reuse each
scraper independently or stitch them together via the report generator.

## Available scrapers

### Economic calendar – `EconScraper.py`
- Fetches economic calendar data from the Trading Economics API.
- Defaults to the public `guest:guest` credentials but you can override them
  with the `TRADING_ECONOMICS_CLIENT` and `TRADING_ECONOMICS_SECRET`
  environment variables.
- Example:
  ```python
  from datetime import date, timedelta
  from EconScraper import fetch_week_ahead

  events = fetch_week_ahead(countries=["United States"])
  ```

### Earnings calendar – `EarningsScraper.py`
- Downloads earnings releases from the Nasdaq calendar API.
- Supports fetching data for a single day or a range (great for the weekly
  lookahead use-case).
- Example:
  ```python
  from datetime import date, timedelta
  from EarningsScraper import fetch_earnings

  start = date.today()
  earnings = fetch_earnings(start=start, end=start + timedelta(days=6))
  ```

### Twitter monitoring – `TwitterScraper.py`
- Minimal wrapper around the Twitter API v2 to pull recent tweets from a list of
  handles.
- Requires a bearer token set via `TWITTER_BEARER_TOKEN` or provided directly to
  `fetch_recent_tweets`.
- Example:
  ```python
  from TwitterScraper import fetch_recent_tweets

  tweets = fetch_recent_tweets(["openai", "markets"])
  ```

### Reddit monitoring – `RedditScraper.py`
- Retrieves the latest posts from subreddits and/or user submissions through
  Reddit's public JSON feeds.
- Example:
  ```python
  from RedditScraper import fetch_reddit_updates

  posts = fetch_reddit_updates(subreddits=["stocks"], users=["wallstreetbets"])
  ```

## Combining everything – `ReportGenerator.py`

`ReportGenerator.py` coordinates the individual scrapers and produces a Markdown
report suitable for feeding into a local LLM or your research workflow.

```
python ReportGenerator.py \
  --lookahead 7 \
  --twitter "openai,bespokeinvest" \
  --reddit-subreddits "stocks,wallstreetbets" \
  --reddit-users "u/someuser" \
  --output weekly_market_brief.md
```

Key options:
- `--start YYYY-MM-DD` – report start date (defaults to today).
- `--lookahead N` – number of days to include after the start date (use 7 for a
  week-ahead view).
- `--twitter` – comma-separated list of Twitter handles.
- `--reddit-subreddits` / `--reddit-users` – comma-separated lists of subreddits
  or Reddit users to track.
- `--skip-*` flags allow you to omit any of the data sources when needed.

The generated Markdown file contains clearly separated sections for the economic
calendar, earnings releases, Twitter highlights, and Reddit highlights.  Each
scraper also exposes helper functions (`events_to_markdown`,
`earnings_to_markdown`, etc.) if you want to embed their outputs in your own
reports.
