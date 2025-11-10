"""Combine scraper outputs into a single Markdown report."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from EconScraper import EconomicEvent, events_to_markdown, fetch_economic_calendar
from EarningsScraper import EarningsEvent, earnings_to_markdown, fetch_earnings
from RedditScraper import RedditPost, fetch_reddit_updates, reddit_to_markdown
from TwitterScraper import Tweet, fetch_recent_tweets, tweets_to_markdown


def _daterange(start: date, lookahead: int) -> tuple[date, date]:
    end = start + timedelta(days=max(0, lookahead))
    return start, end


def collect_economic_data(start: date, lookahead: int) -> List[EconomicEvent]:
    start_date, end_date = _daterange(start, lookahead)
    return fetch_economic_calendar(start=start_date, end=end_date)


def collect_earnings_data(start: date, lookahead: int) -> Dict[date, List[EarningsEvent]]:
    start_date, end_date = _daterange(start, lookahead)
    return fetch_earnings(start=start_date, end=end_date)


def collect_twitter_data(handles: Iterable[str], **kwargs) -> Dict[str, List[Tweet]]:
    handles = [handle.strip() for handle in handles if handle and handle.strip()]
    if not handles:
        return {}
    return fetch_recent_tweets(handles, **kwargs)


def collect_reddit_data(
    *, subreddits: Iterable[str], users: Iterable[str], limit: int
) -> Dict[str, List[RedditPost]]:
    return fetch_reddit_updates(subreddits=subreddits, users=users, limit=limit)


def build_markdown_report(
    *,
    generated_at: datetime,
    economic_events: Optional[List[EconomicEvent]] = None,
    earnings_events: Optional[Dict[date, List[EarningsEvent]]] = None,
    twitter_posts: Optional[Dict[str, List[Tweet]]] = None,
    reddit_posts: Optional[Dict[str, List[RedditPost]]] = None,
) -> str:
    lines = [
        "# Market Intelligence Report",
        f"_Generated on {generated_at.strftime('%Y-%m-%d %H:%M %Z')}_",
        "",
    ]

    if economic_events is not None:
        lines.append("## Economic Calendar")
        lines.append(events_to_markdown(economic_events))

    if earnings_events is not None:
        lines.append("## Earnings Calendar")
        lines.append(earnings_to_markdown(earnings_events))

    if twitter_posts is not None:
        lines.append("## Twitter Highlights")
        lines.append(tweets_to_markdown(twitter_posts))

    if reddit_posts is not None:
        lines.append("## Reddit Highlights")
        lines.append(reddit_to_markdown(reddit_posts))

    return "\n".join(lines).strip() + "\n"


def parse_handles(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a consolidated market report.")
    parser.add_argument("--output", type=Path, default=Path("market_report.md"))
    parser.add_argument(
        "--start", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(), default=date.today()
    )
    parser.add_argument("--lookahead", type=int, default=0, help="Number of days ahead to include")
    parser.add_argument(
        "--twitter",
        type=str,
        help="Comma-separated list of Twitter handles to include (without @ is fine)",
    )
    parser.add_argument(
        "--reddit-subreddits", type=str, help="Comma-separated list of subreddits (without r/)",
    )
    parser.add_argument("--reddit-users", type=str, help="Comma-separated list of reddit usernames")
    parser.add_argument("--reddit-limit", type=int, default=5, help="Number of posts per subreddit/user")
    parser.add_argument("--skip-economic", action="store_true")
    parser.add_argument("--skip-earnings", action="store_true")
    parser.add_argument("--skip-twitter", action="store_true")
    parser.add_argument("--skip-reddit", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_arguments(argv)
    start_date: date = args.start
    lookahead: int = args.lookahead

    economic_events = None
    earnings_events = None
    twitter_posts = None
    reddit_posts = None

    try:
        if not args.skip_economic:
            economic_events = collect_economic_data(start_date, lookahead)
    except Exception as exc:  # pragma: no cover - network dependent
        economic_events = []
        print(f"Failed to fetch economic data: {exc}", file=sys.stderr)

    try:
        if not args.skip_earnings:
            earnings_events = collect_earnings_data(start_date, lookahead)
    except Exception as exc:  # pragma: no cover - network dependent
        earnings_events = {}
        print(f"Failed to fetch earnings data: {exc}", file=sys.stderr)

    twitter_handles = parse_handles(args.twitter)
    try:
        if not args.skip_twitter and twitter_handles:
            twitter_posts = collect_twitter_data(twitter_handles)
    except Exception as exc:  # pragma: no cover - network dependent
        twitter_posts = {}
        print(f"Failed to fetch twitter data: {exc}", file=sys.stderr)

    reddit_subs = parse_handles(args.reddit_subreddits)
    reddit_users = parse_handles(args.reddit_users)
    try:
        if not args.skip_reddit and (reddit_subs or reddit_users):
            reddit_posts = collect_reddit_data(
                subreddits=reddit_subs, users=reddit_users, limit=args.reddit_limit
            )
    except Exception as exc:  # pragma: no cover - network dependent
        reddit_posts = {}
        print(f"Failed to fetch reddit data: {exc}", file=sys.stderr)

    report = build_markdown_report(
        generated_at=datetime.now(timezone.utc),
        economic_events=economic_events,
        earnings_events=earnings_events,
        twitter_posts=twitter_posts,
        reddit_posts=reddit_posts,
    )

    args.output.write_text(report, encoding="utf-8")
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
