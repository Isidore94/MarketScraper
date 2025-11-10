"""Fetch recent posts from Reddit subreddits or users."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import requests

BASE_URL = "https://www.reddit.com"
HEADERS = {"User-Agent": "MarketScraperBot/0.1"}


def _parse_timestamp(timestamp: Optional[float]) -> str:
    if not timestamp:
        return ""
    dt = _dt.datetime.utcfromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


@dataclass
class RedditPost:
    id: str
    title: str
    author: str
    permalink: str
    created_utc: Optional[float]
    url: str

    @classmethod
    def from_listing(cls, data: Dict[str, object]) -> "RedditPost":
        info = data.get("data", {}) if isinstance(data, dict) else {}
        permalink = info.get("permalink", "")
        return cls(
            id=str(info.get("id", "")),
            title=str(info.get("title", "")),
            author=str(info.get("author", "")),
            permalink=permalink,
            created_utc=float(info.get("created_utc", 0) or 0),
            url=f"{BASE_URL}{permalink}" if permalink else str(info.get("url", "")),
        )

    @property
    def created_at(self) -> str:
        return _parse_timestamp(self.created_utc)


class RedditScraperError(RuntimeError):
    """Raised when Reddit returns an unexpected response."""


def _fetch_listing(path: str, *, limit: int, session: requests.Session) -> List[RedditPost]:
    response = session.get(f"{BASE_URL}{path}", params={"limit": limit}, headers=HEADERS, timeout=30)
    if response.status_code >= 400:
        raise RedditScraperError(f"Error fetching {path}: {response.status_code}")
    payload = response.json()
    children = (payload or {}).get("data", {}).get("children", [])
    return [RedditPost.from_listing(child) for child in children]


def fetch_reddit_updates(
    *,
    subreddits: Iterable[str] = (),
    users: Iterable[str] = (),
    limit: int = 10,
    session: Optional[requests.Session] = None,
) -> Dict[str, List[RedditPost]]:
    """Fetch the newest posts for the specified subreddits and users."""

    session = session or requests.Session()
    results: Dict[str, List[RedditPost]] = {}

    for subreddit in subreddits:
        name = subreddit.lstrip('r/').strip()
        key = f"r/{name}"
        path = f"/r/{name}/new.json"
        results[key] = _fetch_listing(path, limit=limit, session=session)

    for user in users:
        username = user.lstrip("u/").strip()
        key = f"u/{username}"
        path = f"/user/{username}/submitted.json"
        results[key] = _fetch_listing(path, limit=limit, session=session)

    return results


def reddit_to_markdown(posts: Dict[str, List[RedditPost]]) -> str:
    if not posts:
        return "No Reddit activity found.\n"

    lines: List[str] = []
    for source, entries in posts.items():
        lines.append(f"### {source}")
        if not entries:
            lines.append("No new posts.\n")
            continue
        for post in entries:
            lines.append(
                f"- [{post.created_at}]({post.url}) {post.title}"
                f" by u/{post.author}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


__all__ = ["RedditPost", "RedditScraperError", "fetch_reddit_updates", "reddit_to_markdown"]
