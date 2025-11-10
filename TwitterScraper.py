"""Simple helper for fetching tweets via the Twitter API v2."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import requests

USER_LOOKUP_URL = "https://api.twitter.com/2/users/by"
USER_TIMELINE_URL = "https://api.twitter.com/2/users/{user_id}/tweets"


def _default_bearer_token(provided: Optional[str]) -> str:
    token = provided or os.getenv("TWITTER_BEARER_TOKEN")
    if not token:
        raise RuntimeError(
            "A Twitter API bearer token is required. Supply it via the "
            "'bearer_token' argument or set the TWITTER_BEARER_TOKEN "
            "environment variable."
        )
    return token


@dataclass
class Tweet:
    id: str
    author_id: str
    text: str
    created_at: Optional[str]
    url: str

    @classmethod
    def from_api(cls, payload: Dict[str, str]) -> "Tweet":
        tweet_id = payload.get("id", "")
        author_id = payload.get("author_id", "")
        created_at = payload.get("created_at")
        return cls(
            id=tweet_id,
            author_id=author_id,
            text=payload.get("text", ""),
            created_at=created_at,
            url=f"https://twitter.com/{author_id}/status/{tweet_id}" if tweet_id else "",
        )


class TwitterScraperError(RuntimeError):
    """Raised when the Twitter API returns an error response."""


def _lookup_user_ids(handles: Iterable[str], session: requests.Session, headers: Dict[str, str]) -> Dict[str, str]:
    usernames = ",".join([handle.lstrip("@") for handle in handles])
    if not usernames:
        return {}
    response = session.get(
        USER_LOOKUP_URL,
        params={"usernames": usernames, "user.fields": "username"},
        headers=headers,
        timeout=30,
    )
    data = response.json()
    if "errors" in data:
        raise TwitterScraperError(str(data["errors"]))
    return {entry["username"].lower(): entry["id"] for entry in data.get("data", [])}


def fetch_recent_tweets(
    handles: Iterable[str],
    *,
    bearer_token: Optional[str] = None,
    max_results: int = 10,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, List[Tweet]]:
    """Retrieve recent tweets for the provided Twitter handles.

    Parameters
    ----------
    handles:
        Iterable of Twitter handles or usernames. ``@`` prefixes are optional.
    bearer_token:
        Twitter API v2 bearer token. If omitted, the function will use the
        ``TWITTER_BEARER_TOKEN`` environment variable.
    max_results:
        Maximum number of tweets to return per handle (max 100 per the API).
    start_time, end_time:
        Optional ISO-8601 timestamps to bound the query.
    session:
        Optional ``requests.Session`` for connection pooling.
    """

    token = _default_bearer_token(bearer_token)
    headers = {"Authorization": f"Bearer {token}"}
    session = session or requests.Session()

    handles = list(handles)
    id_mapping = _lookup_user_ids(handles, session=session, headers=headers)

    tweets: Dict[str, List[Tweet]] = {handle: [] for handle in handles}
    for handle in handles:
        username = handle.lstrip("@")
        user_id = id_mapping.get(username.lower())
        if not user_id:
            continue
        params = {
            "max_results": max(5, min(max_results, 100)),
            "tweet.fields": "created_at,author_id",
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        response = session.get(
            USER_TIMELINE_URL.format(user_id=user_id),
            params=params,
            headers=headers,
            timeout=30,
        )
        data = response.json()
        if "errors" in data:
            raise TwitterScraperError(str(data["errors"]))
        tweets[handle] = [Tweet.from_api(tweet) for tweet in data.get("data", [])]
    return tweets


def tweets_to_markdown(tweets: Dict[str, List[Tweet]]) -> str:
    if not tweets:
        return "No tweets collected.\n"

    lines = []
    for handle, items in tweets.items():
        lines.append(f"### @{handle.lstrip('@')}")
        if not items:
            lines.append("No recent tweets found.\n")
            continue
        for tweet in items:
            timestamp = tweet.created_at or ""
            lines.append(f"- [{timestamp}]({tweet.url}) {tweet.text.strip()}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


__all__ = ["Tweet", "TwitterScraperError", "fetch_recent_tweets", "tweets_to_markdown"]
