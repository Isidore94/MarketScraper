"""Fetch earnings calendar data from Nasdaq's public API."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

BASE_URL = "https://api.nasdaq.com/api/calendar/earnings"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

DATE_FORMAT = "%Y-%m-%d"


@dataclass
class EarningsEvent:
    """Representation of a single earnings announcement."""

    symbol: str
    company: str
    date: _dt.date
    eps_estimate: Optional[str]
    eps_actual: Optional[str]
    time: Optional[str]

    @classmethod
    def from_api(cls, row: Dict[str, str], on_date: _dt.date) -> "EarningsEvent":
        return cls(
            symbol=row.get("symbol", "").strip(),
            company=row.get("companyName", "").strip(),
            date=on_date,
            eps_estimate=row.get("epsForecast"),
            eps_actual=row.get("epsActual"),
            time=row.get("time") or row.get("timeZone"),
        )


class EarningsCalendarError(RuntimeError):
    """Raised when the Nasdaq API returns an unexpected response."""


def _coerce_date(value: Optional[_dt.date | str]) -> _dt.date:
    if value is None:
        return _dt.date.today()
    if isinstance(value, _dt.date):
        return value
    return _dt.datetime.strptime(value, DATE_FORMAT).date()


def _fetch_for_date(on_date: _dt.date, session: requests.Session, timeout: int) -> List[EarningsEvent]:
    params = {"date": on_date.strftime(DATE_FORMAT)}
    response = session.get(BASE_URL, params=params, headers=HEADERS, timeout=timeout)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - network dependent
        raise EarningsCalendarError(str(exc)) from exc

    data = response.json()
    rows = (data or {}).get("data", {}).get("rows", [])
    if rows is None:
        rows = []
    events = [EarningsEvent.from_api(row, on_date) for row in rows]
    return events


def fetch_earnings(
    start: Optional[_dt.date | str] = None,
    end: Optional[_dt.date | str] = None,
    *,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
) -> Dict[_dt.date, List[EarningsEvent]]:
    """Fetch earnings events for a date range.

    If only ``start`` is supplied, ``end`` defaults to the same day.  When
    neither is provided the function returns the current day's earnings.
    """

    start_date = _coerce_date(start)
    end_date = _coerce_date(end) if end else start_date
    if end_date < start_date:
        raise ValueError("end date must be after start date")

    session = session or requests.Session()
    current = start_date
    events: Dict[_dt.date, List[EarningsEvent]] = {}

    while current <= end_date:
        events[current] = _fetch_for_date(current, session=session, timeout=timeout)
        current += _dt.timedelta(days=1)

    return events


def fetch_week_ahead(**kwargs) -> Dict[_dt.date, List[EarningsEvent]]:
    start = kwargs.pop("start", _dt.date.today())
    end = kwargs.pop("end", start + _dt.timedelta(days=6))
    return fetch_earnings(start=start, end=end, **kwargs)


def earnings_to_markdown(events: Dict[_dt.date, List[EarningsEvent]]) -> str:
    """Render the collected earnings information to Markdown."""

    if not events:
        return "No earnings events found.\n"

    lines = []
    for event_date in sorted(events):
        lines.append(f"### {event_date.strftime('%A, %B %d, %Y')}")
        day_events = events[event_date]
        if not day_events:
            lines.append("No scheduled earnings releases.\n")
            continue
        lines.append(
            "| Symbol | Company | Time | EPS Estimate | EPS Actual |\n"
            "|---|---|---|---|---|"
        )
        for event in day_events:
            lines.append(
                f"| {event.symbol} | {event.company} | {event.time or ''} | "
                f"{event.eps_estimate or ''} | {event.eps_actual or ''} |"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


__all__ = [
    "EarningsEvent",
    "EarningsCalendarError",
    "fetch_earnings",
    "fetch_week_ahead",
    "earnings_to_markdown",
]
