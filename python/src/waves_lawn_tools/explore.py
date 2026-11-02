"""Waves Lawn Tools: waves_lawn_tools.explore

Small pure helpers that shape answers from the Waves public API into rows and short
facts for a table, a chart or an app (the Streamlit app in ``apps/streamlit`` uses
them). They take the decoded API answers and return plain Python lists and dicts. They
make no network calls.

MIT License. Copyright (c) 2026 Waves Pest Control, LLC.
"""

from __future__ import annotations

import urllib.error
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .api import WavesApiError

SITE_URL = "https://www.wavespestcontrol.com"
WATERING_PAGE = SITE_URL + "/tools/lawn-watering-calculator/"
FORECAST_PAGE = SITE_URL + "/tools/pest-pressure-forecast/"
YARD_CALENDAR_PAGE = SITE_URL + "/tools/swfl-lawn-pest-calendar/"
INDEX_PAGE = SITE_URL + "/pest-pressure-index/"

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
MONTH_ABBREVIATIONS = tuple(name[:3] for name in MONTH_NAMES)

# (watering-plan grass value, yard-calendar grass code, label)
GRASS_TYPES: Tuple[Tuple[str, str, str], ...] = (
    ("st_augustine", "sta", "St. Augustine"),
    ("bahia", "bah", "Bahia"),
    ("zoysia", "zoy", "Zoysia"),
    ("bermuda", "ber", "Bermuda"),
    ("unknown", "all", "Not sure"),
)

CATEGORY_LABELS = {
    "lawn": "Lawn",
    "weed": "Weed",
    "shrub": "Shrub and tree",
}

TREND_LABELS = {
    "easing_next_month": "Easing next month",
    "peak_next_month": "Peaking next month",
    "starts_next_month": "Starts next month",
    "rising": "Rising",
    "falling": "Falling",
    "flat": "Steady",
}

DEFAULT_SCALE_LABELS = {0: "None", 1: "Very Low", 2: "Low", 3: "Moderate", 4: "Elevated", 5: "High"}


def month_name(month: int) -> str:
    """``month_name(11)`` is ``"November"``. Raises ValueError outside 1 to 12."""
    if not isinstance(month, int) or isinstance(month, bool) or not 1 <= month <= 12:
        raise ValueError("month must be an integer from 1 to 12")
    return MONTH_NAMES[month - 1]


def grass_label(grass: str) -> str:
    """The label for either kind of grass value (``st_augustine`` or ``sta``); unknown values pass through."""
    for watering, calendar, label in GRASS_TYPES:
        if grass in (watering, calendar):
            return label
    return str(grass)


def calendar_grass_code(grass: str) -> str:
    """The yard-calendar code for a watering-plan grass value (``st_augustine`` becomes ``sta``).

    A value that is already a calendar code stays; anything unrecognized becomes ``all``.
    """
    for watering, calendar, _ in GRASS_TYPES:
        if grass in (watering, calendar):
            return calendar
    return "all"


def watering_grass_value(grass: str) -> str:
    """The watering-plan grass value for either kind (``sta`` becomes ``st_augustine``); unknown becomes ``unknown``."""
    for watering, calendar, _ in GRASS_TYPES:
        if grass in (watering, calendar):
            return watering
    return "unknown"


def location_choices(locations: Sequence[Mapping[str, Any]]) -> List[Tuple[str, str]]:
    """``[(slug, label), ...]`` for a city picker, in the order the API gives them."""
    return [(loc["slug"], loc.get("label") or loc["slug"]) for loc in locations if loc.get("slug")]


def _number(value: Any, digits: int = 2) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), digits)


def _inches(value: Any) -> str:
    n = _number(value)
    return "n/a" if n is None else f'{n:g}"'


def watering_plan_facts(plan: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """Label and value pairs for the key facts of a watering-plan answer.

    Missing parts are skipped, so a ``need_only`` or ``unavailable`` answer still works.
    """
    facts: List[Tuple[str, str]] = []
    decision = plan.get("plan") or {}
    action = decision.get("action")
    if action:
        facts.append(("Decision", {"run": "Water", "hold": "Hold off", "need_only": "Need only (no watering order tracked)"}.get(action, str(action).replace("_", " ").capitalize())))
    if decision.get("events") is not None and action == "run":
        facts.append(("Waterings this week", str(decision["events"])))
    if decision.get("depthInches") is not None:
        facts.append(("Water per run", _inches(decision["depthInches"])))
    if decision.get("minutesPerEvent") is not None:
        facts.append(("Minutes per zone", str(decision["minutesPerEvent"])))
    if decision.get("legalMaxEvents") is not None:
        facts.append(("Legal days per week", str(decision["legalMaxEvents"])))
    need = plan.get("need") or {}
    if need.get("targetInches") is not None:
        facts.append(("Lawn need this week", _inches(need["targetInches"])))
    if need.get("netInches") is not None:
        facts.append(("Need after recent rain", _inches(need["netInches"])))
    rain = plan.get("rain") or {}
    if rain.get("last7Inches") is not None:
        facts.append(("Rain, last 7 days", _inches(rain["last7Inches"])))
    forecast = plan.get("forecast") or {}
    if forecast.get("rainInches") is not None:
        facts.append(("Rain forecast, next 7 days", _inches(forecast["rainInches"])))
    if forecast.get("et0Inches") is not None:
        facts.append(("Evapotranspiration forecast", _inches(forecast["et0Inches"])))
    restriction = plan.get("restriction") or {}
    if restriction.get("label"):
        facts.append(("Local watering limit", str(restriction["label"])))
    return facts


def watering_plan_text(plan: Mapping[str, Any]) -> Dict[str, Any]:
    """The prose of an answer: ``headline``, ``action`` and ``notes`` (a list), with safe defaults."""
    text = plan.get("text") or {}
    notes = text.get("notes")
    return {
        "headline": text.get("headline") or "",
        "action": text.get("action") or "",
        "notes": [str(n) for n in notes] if isinstance(notes, list) else [],
    }


def pest_forecast_rows(forecast: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """One row per pest, highest score first: Pest, Level, Score, Versus normal, Trend, Note."""
    rows = []
    for pest in forecast.get("pests") or []:
        comparison = pest.get("baseline_comparison")
        rows.append(
            {
                "Pest": pest.get("label") or pest.get("key") or "",
                "Level": str(pest.get("level") or "").capitalize(),
                "Score": pest.get("score10", pest.get("score")),
                "Versus normal": {"above": "Above normal", "below": "Below normal", "near": "Near normal"}.get(comparison, comparison or ""),
                "Trend": TREND_LABELS.get(pest.get("trend"), str(pest.get("trend") or "").replace("_", " ").capitalize()),
                "Note": pest.get("note") or "",
            }
        )
    rows.sort(key=lambda r: (-(r["Score"] if isinstance(r["Score"], (int, float)) else -1), r["Pest"]))
    return rows


def pest_forecast_summary(forecast: Mapping[str, Any]) -> Dict[str, str]:
    """``month`` (name), ``summary`` (one sentence), ``weather`` (one line) and ``disclaimer``."""
    weather = forecast.get("weather") or {}
    return {
        "month": str(forecast.get("month_name") or ""),
        "summary": str(forecast.get("summary") or ""),
        "weather": str(weather.get("summary") or "") if weather.get("available", True) else "",
        "disclaimer": str(forecast.get("disclaimer") or ""),
    }


def absolute_url(link: Optional[str]) -> Optional[str]:
    """Turn a site-relative link such as ``/pest-identifier/chinch-bug/`` into a wavespestcontrol.com URL."""
    if not link:
        return None
    if link.startswith("//"):
        return None
    if link.startswith("/"):
        return SITE_URL + link
    return link if link.startswith("https://") else None


def yard_calendar_rows(
    calendar: Mapping[str, Any], categories: Optional[Sequence[str]] = None, include_info_only: bool = False
) -> List[Dict[str, Any]]:
    """One row per yard item for the month, most active first.

    Columns: Name, Type, Level (0 to 3), Status, Trend, Hosts, What to look for, Learn more.
    ``categories`` keeps only ``lawn``, ``weed`` or ``shrub`` items. Info-only items are
    left out unless ``include_info_only``.
    """
    rows = []
    for item in calendar.get("items") or []:
        if categories is not None and item.get("category") not in categories:
            continue
        if item.get("infoOnly") and not include_info_only:
            continue
        category = item.get("category") or ""
        rows.append(
            {
                "Name": item.get("name") or item.get("id") or "",
                "Type": CATEGORY_LABELS.get(category, category.capitalize()),
                "Level": item.get("level", 0),
                "Status": item.get("levelLabel") or "",
                "Trend": TREND_LABELS.get(item.get("trend"), "") if item.get("trend") else "",
                "Hosts": item.get("hosts") or "",
                "What to look for": item.get("sign") or "",
                "Learn more": absolute_url(item.get("link")),
            }
        )
    rows.sort(key=lambda r: (-(r["Level"] if isinstance(r["Level"], (int, float)) else 0), r["Name"]))
    return rows


def yard_year_rows(calendar: Mapping[str, Any], include_info_only: bool = False) -> List[Dict[str, Any]]:
    """One row per yard item with its level (0 to 3) for each month: Name, then Jan to Dec."""
    rows = []
    for item in calendar.get("items") or []:
        if item.get("infoOnly") and not include_info_only:
            continue
        levels = item.get("levels") or []
        row: Dict[str, Any] = {"Name": item.get("name") or item.get("id") or ""}
        for index, abbreviation in enumerate(MONTH_ABBREVIATIONS):
            row[abbreviation] = levels[index] if index < len(levels) else None
        rows.append(row)
    return rows


def plan_ahead(calendar: Mapping[str, Any]) -> List[str]:
    """What to plan for now, as a list of strings (empty when the answer has none)."""
    items = calendar.get("planAhead")
    return [str(i) for i in items] if isinstance(items, list) else []


def rating_label(average: float, scale: Optional[Mapping[str, Any]] = None) -> str:
    """The scale word nearest an average rating, for example 2.2 gives ``Low``.

    ``scale`` is the ``scale`` object of the index answer (with ``labels``); without it the
    standard 0 to 5 labels are used. Halves round up.
    """
    labels: Dict[int, str] = dict(DEFAULT_SCALE_LABELS)
    if scale and isinstance(scale.get("labels"), Mapping):
        for key, value in scale["labels"].items():
            try:
                labels[int(key)] = str(value)
            except (TypeError, ValueError):
                continue
    low, high = min(labels), max(labels)
    nearest = int(average + 0.5)
    return labels[max(low, min(high, nearest))]


def pressure_index_rows(index: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """One row per county and service line, busiest first.

    Columns: County, Service, Visits, Average (0 to 5), Median, Rating. Service names are
    shown capitalized (``pest`` becomes ``Pest``).
    """
    scale = index.get("scale")
    rows = []
    for group in index.get("groups") or []:
        average = group.get("average")
        rows.append(
            {
                "County": group.get("county") or "",
                "Service": str(group.get("service_line") or "").replace("_", " ").capitalize(),
                "Visits": group.get("visits"),
                "Average (0 to 5)": average,
                "Median": group.get("median"),
                "Rating": rating_label(average, scale) if isinstance(average, (int, float)) else "",
            }
        )
    rows.sort(key=lambda r: (-(r["Average (0 to 5)"] if isinstance(r["Average (0 to 5)"], (int, float)) else -1), r["County"]))
    return rows


def pressure_index_caption(index: Mapping[str, Any]) -> str:
    """One paragraph that says what the table is: window, minimum visits, hidden groups, license."""
    window = index.get("window") or {}
    parts = []
    if window.get("start") and window.get("end"):
        parts.append(f"Completed Waves service visits from {window['start']} to {window['end']}.")
    if index.get("min_visits"):
        parts.append(f"A group shows only with {index['min_visits']} or more visits.")
    hidden = index.get("hidden_groups")
    if isinstance(hidden, int) and hidden > 0:
        parts.append(f"{hidden} smaller {'group is' if hidden == 1 else 'groups are'} left out.")
    parts.append("Averages of the technician's on-site pest activity rating, not a survey and not a forecast.")
    license_ = index.get("license") or {}
    if license_.get("name"):
        parts.append(f"License: {license_['name']}.")
    return " ".join(parts)


def friendly_error(error: BaseException) -> str:
    """A short message for a person who hit an API failure."""
    if isinstance(error, WavesApiError):
        if error.status == 429:
            return "The Waves API is busy (limit: 120 requests in 15 minutes). Please try again in a few minutes."
        if error.status == 503:
            return "The weather data behind this answer is down right now. Please try again later."
        if 400 <= error.status < 500:
            return f"The Waves API could not use that choice: {error.message}"
        return "The Waves API had a problem. Please try again later."
    if isinstance(error, (urllib.error.URLError, TimeoutError, OSError)):
        return "Could not reach the Waves API. Check your connection and try again."
    return "Something went wrong while loading this section. Please try again."
