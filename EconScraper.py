"""Utilities for downloading economic calendar data from Trading Economics.

This module interacts with the Trading Economics public API to retrieve
upcoming economic events.  By default it uses the guest credentials supplied
by Trading Economics, but the client and secret can be overridden via
arguments or the ``TRADING_ECONOMICS_CLIENT`` and ``TRADING_ECONOMICS_SECRET``
environment variables.

Example
-------
>>> from datetime import date, timedelta
>>> from EconScraper import fetch_economic_calendar
>>> start = date.today()
>>> end = start + timedelta(days=7)
>>> events = fetch_economic_calendar(start, end, countries=["United States"])
>>> print(events[0]["Event"])
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import List, Mapping, Optional, Sequence

import requests

BASE_URL = "https://api.tradingeconomics.com/calendar"
DATE_FORMAT = "%Y-%m-%d"


class EconomicEvent(Mapping[str, object]):
    """Dictionary-like representation of a Trading Economics event.

    The API already returns dictionaries, but this wrapper gives us type hints
    and the flexibility to add helper properties without breaking backwards
    compatibility.
    """

    def __init__(self, payload: Mapping[str, object]) -> None:
        self._payload = dict(payload)

    def __getitem__(self, key: str) -> object:
        return self._payload[key]

    def __iter__(self):
        return iter(self._payload)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._payload)

    @property
    def country(self) -> Optional[str]:
        return self._payload.get("Country") or self._payload.get("country")

    @property
    def category(self) -> Optional[str]:
        return self._payload.get("Category") or self._payload.get("category")

    @property
    def event(self) -> Optional[str]:
        return self._payload.get("Event") or self._payload.get("event")

    @property
    def release_time(self) -> Optional[datetime]:
        release = self._payload.get("DateUTC") or self._payload.get("date")
        if not release:
            return None
        if isinstance(release, datetime):
            return release
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(str(release), fmt)
            except ValueError:
                continue
        return None

    def as_dict(self) -> Mapping[str, object]:
        """Return the raw dictionary."""

        return dict(self._payload)


class EconomicCalendarError(RuntimeError):
    """Raised when the Trading Economics API returns an unexpected response."""


def _resolve_credentials(
    client: Optional[str], secret: Optional[str]
) -> str:
    resolved_client = client or os.getenv("TRADING_ECONOMICS_CLIENT", "guest")
    resolved_secret = secret or os.getenv("TRADING_ECONOMICS_SECRET", "guest")
    return f"{resolved_client}:{resolved_secret}"


def _build_params(
    start: date,
    end: date,
    importance: Optional[Sequence[str]] = None,
    countries: Optional[Sequence[str]] = None,
    categories: Optional[Sequence[str]] = None,
) -> Mapping[str, str]:
    if end < start:
        raise ValueError("end date must be after start date")

    params = {
        "start": start.strftime(DATE_FORMAT),
        "end": end.strftime(DATE_FORMAT),
        "format": "json",
    }

    if importance:
        params["importance"] = ",".join(importance)
    if countries:
        params["country"] = ",".join(countries)
    if categories:
        params["category"] = ",".join(categories)
    return params


def fetch_economic_calendar(
    start: Optional[date] = None,
    end: Optional[date] = None,
    *,
    importance: Optional[Sequence[str]] = None,
    countries: Optional[Sequence[str]] = None,
    categories: Optional[Sequence[str]] = None,
    client: Optional[str] = None,
    secret: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
) -> List[EconomicEvent]:
    """Fetch economic events from Trading Economics.

    Parameters
    ----------
    start, end:
        ``datetime.date`` boundaries for the query. ``start`` defaults to
        today and ``end`` defaults to the same day.  Use ``end = start +
        timedelta(days=6)`` to retrieve a week of data.
    importance:
        Optional collection of importance values ("1", "2", "3").
    countries, categories:
        Optional filters matching Trading Economics API parameters.
    client, secret:
        Trading Economics API credentials.  These fall back to the environment
        variables ``TRADING_ECONOMICS_CLIENT`` and ``TRADING_ECONOMICS_SECRET``
        and finally to the public ``guest`` credentials.
    session:
        Optional ``requests.Session`` for connection pooling.
    timeout:
        Request timeout in seconds.
    """

    start = start or date.today()
    end = end or start

    params = dict(_build_params(start, end, importance, countries, categories))
    params["c"] = _resolve_credentials(client, secret)

    http = session or requests.Session()
    response = http.get(BASE_URL, params=params, timeout=timeout)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - network dependent
        raise EconomicCalendarError(str(exc)) from exc

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - network dependent
        raise EconomicCalendarError("Invalid JSON returned from API") from exc

    if not isinstance(payload, list):
        raise EconomicCalendarError("Unexpected payload structure")

    return [EconomicEvent(event) for event in payload]


def fetch_week_ahead(**kwargs) -> List[EconomicEvent]:
    """Convenience wrapper for retrieving the next seven days of events."""

    start = kwargs.pop("start", date.today())
    end = kwargs.pop("end", start + timedelta(days=6))
    return fetch_economic_calendar(start=start, end=end, **kwargs)


def events_to_markdown(events: Sequence[EconomicEvent]) -> str:
    """Format economic events as a markdown table."""

    if not events:
        return "No economic events found.\n"

    header = "| Date | Time (UTC) | Country | Event | Actual | Forecast | Previous |"\
        "\n|---|---|---|---|---|---|---|"
    rows = []
    for event in events:
        data = event.as_dict()
        when = data.get("DateUtc") or data.get("DateUTC") or data.get("Date")
        time = data.get("Time") or ""
        rows.append(
            "| {date} | {time} | {country} | {event} | {actual} | {forecast} |"
            " {previous} |".format(
                date=when or "",
                time=time,
                country=data.get("Country", ""),
                event=data.get("Event", ""),
                actual=data.get("Actual", ""),
                forecast=data.get("Forecast", ""),
                previous=data.get("Previous", ""),
            )
        )
    return "\n".join([header, *rows]) + "\n"


__all__ = [
    "EconomicEvent",
    "EconomicCalendarError",
    "fetch_economic_calendar",
    "fetch_week_ahead",
    "events_to_markdown",
]
