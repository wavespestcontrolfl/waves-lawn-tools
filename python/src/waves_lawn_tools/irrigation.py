"""Waves Lawn Tools: waves_lawn_tools.irrigation

https://github.com/wavespestcontrolfl/waves-lawn-tools

The lawn-watering math behind the free Lawn Watering Calculator
(https://www.wavespestcontrol.com/tools/lawn-watering-calculator/). It is a port of
``src/irrigation.js`` in the same repository, and ``python/tests`` checks it against
that file's output case by case, so the two cannot drift. The code reads no environment
and calls no network.

MIT License. Copyright (c) 2026 Waves Pest Control, LLC. See LICENSE.

Runtime to inches per week
    inches/week = (minutes / 60) x head rate (in/hr) x watering days/week

Zone count does not enter the formula: the precipitation rate is per area, so every
zone puts down the same depth for the same runtime. Head rates are the UF/IFAS typical
rates for residential systems (AE451, ENH9): fixed spray heads about 1.5 in/hr, rotors
about 0.5 in/hr. They are published defaults, not measurements of your yard.

Drip zones water beds, not turf, and mixed head types put water down at very
different rates. Neither converts to one lawn figure, so both decline with a reason
code rather than guess.

Naming: the JavaScript camelCase names become snake_case (``buildWeekPlan`` is
``build_week_plan``, ``inchesPerWeek`` is ``inches_per_week``). Results are plain
dicts. Numbers follow JavaScript rules where they differ from Python (``Math.round``
rounds .5 up, ``Number()`` coercion), so the results match the JavaScript exactly.
"""

from __future__ import annotations

import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Optional

__all__ = [
    "DAY_ALIASES",
    "DAY_KEYS",
    "HEAD_LABELS",
    "HEAD_PRECIP_RATE_IN_PER_HR",
    "MAX_INCHES_PER_WEEK",
    "MAX_RUN_MINUTES",
    "OWNER_HEAD_RATE_IN_PER_HR",
    "OWNER_MINUTES_PER_QUARTER_INCH",
    "WEEK_PLAN_CONSTANTS",
    "build_week_plan",
    "default_event_minutes",
    "derive_irrigation_inches_per_week",
    "describe_runtime_basis",
    "normalize_runtime_inputs",
    "resolve_application_rate",
]

# ---------------------------------------------------------------------------
# JavaScript number semantics
# ---------------------------------------------------------------------------

_NAN = float("nan")
_INF = float("inf")

# What String.prototype.trim removes (WhiteSpace and LineTerminator in ECMAScript).
_JS_WHITESPACE = (
    "\t\n\u000b\f\r          "
    "        　﻿"
)

_DECIMAL = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*(?:[eE][+-]?[0-9]+)?|\.[0-9]+(?:[eE][+-]?[0-9]+)?)")


def _js_trim(text: str) -> str:
    return text.strip(_JS_WHITESPACE)


def _js_str(value: Any) -> str:
    """JavaScript ``String(value)`` for the value kinds this module meets."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ",".join("" if item is None else _js_str(item) for item in value)
    if isinstance(value, Mapping):
        return "[object Object]"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value == int(value) and abs(value) < 1e21:
            return str(int(value))
    return str(value)


def _js_number(value: Any) -> float:
    """JavaScript ``Number(value)``: null is 0, '' is 0, '0x10' is 16, junk is NaN."""
    if value is None:
        return 0.0
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    if isinstance(value, int):
        try:
            return float(value)
        except OverflowError:
            return _INF if value > 0 else -_INF
    if isinstance(value, float):
        return value
    if isinstance(value, (list, tuple)):
        return _js_number(_js_str(value))
    if isinstance(value, str):
        text = _js_trim(value)
        if text == "":
            return 0.0
        if re.fullmatch(r"0[xX][0-9a-fA-F]+", text):
            return float(int(text[2:], 16))
        if re.fullmatch(r"0[oO][0-7]+", text):
            return float(int(text[2:], 8))
        if re.fullmatch(r"0[bB][01]+", text):
            return float(int(text[2:], 2))
        if text in ("Infinity", "+Infinity"):
            return _INF
        if text == "-Infinity":
            return -_INF
        if _DECIMAL.fullmatch(text):
            return float(text)
        return _NAN
    return _NAN


def _is_finite(n: float) -> bool:
    return not (math.isnan(n) or math.isinf(n))


def _js_round(x: float) -> Any:
    """JavaScript ``Math.round``: halves round toward +infinity (``round(-2.5)`` is -2).

    Python's ``round`` is banker's rounding, so it cannot be used here. Returns an int
    for a finite input, the input itself for NaN or an infinity.
    """
    if not _is_finite(x):
        return x
    floor = math.floor(x)
    return floor + 1 if x - floor >= 0.5 else floor


def _round2(n: float) -> float:
    return _js_round(n * 100) / 100


def _round_to_5(n: float) -> Any:
    return max(5, _js_round(n / 5) * 5)


def _clamp(n: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, n))


def _finite_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    n = _js_number(value)
    return n if _is_finite(n) else None


def _is_integer(n: float) -> bool:
    return _is_finite(n) and math.floor(n) == n


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEAD_PRECIP_RATE_IN_PER_HR = MappingProxyType({"spray": 1.5, "rotor": 0.5})

# The Waves owner table: minutes a head type runs to put down a quarter inch.
OWNER_MINUTES_PER_QUARTER_INCH = MappingProxyType({"spray": 15, "rotor": 40})
OWNER_HEAD_RATE_IN_PER_HR = MappingProxyType(
    {
        head: _js_round((0.25 / (minutes / 60)) * 1000) / 1000
        for head, minutes in OWNER_MINUTES_PER_QUARTER_INCH.items()
    }
)

HEAD_LABELS = MappingProxyType({"spray": "spray heads", "rotor": "rotor heads", "drip": "drip"})

DAY_KEYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

MAX_RUN_MINUTES = 240

# A derived figure above this (240 min x 7 days on spray is 42 in/week) is a
# data-entry artifact, not a schedule, and declines.
MAX_INCHES_PER_WEEK = 5

# Exact aliases only: a prefix rule would fabricate days out of non-day text
# ("monthly" would become Mon, "sunny" would become Sun).
DAY_ALIASES = MappingProxyType(
    {
        "mon": "Mon", "monday": "Mon",
        "tue": "Tue", "tues": "Tue", "tuesday": "Tue",
        "wed": "Wed", "weds": "Wed", "wednesday": "Wed",
        "thu": "Thu", "thur": "Thu", "thurs": "Thu", "thursday": "Thu",
        "fri": "Fri", "friday": "Fri",
        "sat": "Sat", "saturday": "Sat",
        "sun": "Sun", "sunday": "Sun",
    }
)

# UF/IFAS: apply 1/2 to 3/4 inch per irrigation event, deep and infrequent.
EVENT_DEPTH_MIN_INCHES = 0.5
EVENT_DEPTH_MAX_INCHES = 0.75
# Below one meaningful event there is nothing to schedule.
HOLD_BELOW_INCHES = EVENT_DEPTH_MIN_INCHES
# Last week's surplus is not banked 1:1: Southwest Florida sand drains. Carryover is
# capped at an estimated root-zone storage.
ROOT_ZONE_STORAGE_INCHES = 0.5
# 1/2 inch or more of rain skips the next scheduled run. A forecast at or above it
# makes the plan conditional, not cancelled.
RAIN_SKIP_INCHES = 0.5
# Seasonal ceiling on events even where restrictions allow more.
SEASONAL_MAX_EVENTS = MappingProxyType({"peak": 2, "shoulder": 2, "cool": 1})
# Sanity band for a measured application rate (in/hr).
MEASURED_RATE_MIN = 0.2
MEASURED_RATE_MAX = 4

WEEK_PLAN_CONSTANTS = MappingProxyType(
    {
        "EVENT_DEPTH_MIN_INCHES": EVENT_DEPTH_MIN_INCHES,
        "EVENT_DEPTH_MAX_INCHES": EVENT_DEPTH_MAX_INCHES,
        "HOLD_BELOW_INCHES": HOLD_BELOW_INCHES,
        "ROOT_ZONE_STORAGE_INCHES": ROOT_ZONE_STORAGE_INCHES,
        "RAIN_SKIP_INCHES": RAIN_SKIP_INCHES,
        "SEASONAL_MAX_EVENTS": SEASONAL_MAX_EVENTS,
    }
)


# ---------------------------------------------------------------------------
# Input normalizing
# ---------------------------------------------------------------------------


def _reject_json_constant(name: str) -> Any:
    raise ValueError(name)  # JSON.parse refuses NaN and Infinity


def _to_array(value: Any) -> list:
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str) and _js_trim(value):
        try:
            parsed = json.loads(value, parse_constant=_reject_json_constant)
        except (ValueError, RecursionError):
            return [value]
        return parsed if isinstance(parsed, list) else [value]
    return []


def _positive_int(value: Any, maximum: float) -> Optional[int]:
    n = _js_number(value)
    if not _is_finite(n) or n <= 0:
        return None
    i = _js_round(n)
    return None if i > maximum else i


def _normalize_days(value: Any) -> list:
    seen = {DAY_ALIASES.get(_js_trim(_js_str(d)).lower()) for d in _to_array(value)}
    return [d for d in DAY_KEYS if d in seen]


def _normalize_head_types(value: Any) -> list:
    heads: list = []
    for item in _to_array(value):
        head = _js_trim(_js_str(item)).lower()
        if head and head not in heads:
            heads.append(head)
    return heads


# ---------------------------------------------------------------------------
# Runtime to inches per week
# ---------------------------------------------------------------------------


def derive_irrigation_inches_per_week(
    run_minutes: Any = None,
    watering_days: Any = None,
    system_type: Any = None,
    *,
    rates: Optional[Mapping[str, float]] = None,
    ignore_drip: bool = False,
) -> dict:
    """Turn a sprinkler schedule into inches of water per week.

    ``run_minutes`` is the TOTAL minutes each zone runs on a watering day (cycle-and-soak
    cycles summed). ``watering_days`` is a list like ``["Mon", "Thu"]`` or a JSON string of
    one; full names ("Monday") work. ``system_type`` is a list or JSON string of
    ``"spray"``, ``"rotor"`` or ``"drip"``. ``rates`` swaps the head-rate table (for
    example ``OWNER_HEAD_RATE_IN_PER_HR``). ``ignore_drip`` leaves drip out when counting turf head
    types.

    Returns ``inches_per_week`` (rounded to hundredths, or None), ``reason`` (None, or why
    it declined), ``run_minutes``, ``runs_per_week``, ``head_type`` and ``rate_in_per_hr``.

    Reasons: ``missing_minutes``, ``missing_days``, ``missing_head_type``,
    ``mixed_head_types``, ``drip_only``, ``unknown_head_type``, ``implausible_total``.
    """
    rates = HEAD_PRECIP_RATE_IN_PER_HR if rates is None else rates
    minutes = _positive_int(run_minutes, MAX_RUN_MINUTES)
    days = _normalize_days(watering_days)
    all_heads = _normalize_head_types(system_type)
    heads = [h for h in all_heads if h != "drip"] if ignore_drip else all_heads
    base = {
        "inches_per_week": None,
        "run_minutes": minutes,
        "runs_per_week": len(days),
        "head_type": None,
        "rate_in_per_hr": None,
    }

    if minutes is None:
        return {**base, "reason": "missing_minutes"}
    if not days:
        return {**base, "reason": "missing_days"}
    if not all_heads:
        return {**base, "reason": "missing_head_type"}
    if not heads or (len(heads) == 1 and heads[0] == "drip"):
        return {**base, "reason": "drip_only"}
    if len(heads) > 1:
        return {**base, "reason": "mixed_head_types"}
    rate = rates.get(heads[0])
    if rate is None:
        return {**base, "reason": "unknown_head_type"}

    inches = _js_round(((minutes / 60) * rate * len(days)) * 100) / 100
    if inches > MAX_INCHES_PER_WEEK:
        return {**base, "reason": "implausible_total"}
    return {**base, "inches_per_week": inches, "reason": None, "head_type": heads[0], "rate_in_per_hr": rate}


def describe_runtime_basis(derived: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Plain English for where a derived figure came from, or None.

    Example: ``"20 minutes per zone, 4 days a week on spray heads"``.
    """
    if not derived or derived.get("inches_per_week") is None:
        return None
    runs = derived["runs_per_week"]
    day_word = "day" if runs == 1 else "days"
    head = derived["head_type"]
    return f"{derived['run_minutes']} minutes per zone, {runs} {day_word} a week on {HEAD_LABELS.get(head, head)}"


def normalize_runtime_inputs(run_minutes: Any = None, watering_days: Any = None, system_type: Any = None) -> dict:
    """The three schedule inputs, normalized: ``run_minutes``, ``watering_days``, ``head_types``."""
    return {
        "run_minutes": _positive_int(run_minutes, MAX_RUN_MINUTES),
        "watering_days": _normalize_days(watering_days),
        "head_types": _normalize_head_types(system_type),
    }


# ---------------------------------------------------------------------------
# This week's watering plan: the decision only, no prose.
#
# Recommend the smallest LEGAL irrigation action that keeps an established lawn
# healthy: observed rain and soil-water need first, forecast rain second
# (conditionally, never credited up front), visible turf stress as the final override.
# Precedence: legal restriction, turf need, observed rain and carryover, forecast.
# ---------------------------------------------------------------------------


def resolve_application_rate(
    explicit_inches_per_week: Any = None,
    run_minutes: Any = None,
    watering_days: Any = None,
    system_type: Any = None,
    *,
    rates: Optional[Mapping[str, float]] = None,
) -> dict:
    """Application rate (in/hr) for minutes to depth.

    MEASURED when weekly inches AND a runtime were given (inches / (min/60 x days));
    otherwise the published head-type default; None when neither is available.
    Returns ``rate_in_per_hr``, ``rate_source`` (``measured`` or ``system_type_default``)
    and ``head_type``.
    """
    rates = HEAD_PRECIP_RATE_IN_PER_HR if rates is None else rates
    inputs = normalize_runtime_inputs(run_minutes, watering_days, system_type)
    # A per-zone runtime needs ONE turf head type; mixed, drip-only and unknown systems
    # stay events-only, even when weekly inches were typed.
    turf_heads = [h for h in inputs["head_types"] if h != "drip"]
    if len(turf_heads) != 1 or rates.get(turf_heads[0]) is None:
        return {"rate_in_per_hr": None, "rate_source": None, "head_type": None}
    head_type = turf_heads[0]
    explicit = _finite_or_none(explicit_inches_per_week)
    if explicit is not None and explicit > 0 and inputs["run_minutes"] is not None and inputs["watering_days"]:
        rate = explicit / ((inputs["run_minutes"] / 60) * len(inputs["watering_days"]))
        if MEASURED_RATE_MIN <= rate <= MEASURED_RATE_MAX:
            return {"rate_in_per_hr": _round2(rate), "rate_source": "measured", "head_type": head_type}
    return {"rate_in_per_hr": rates[head_type], "rate_source": "system_type_default", "head_type": head_type}


def default_event_minutes(rates: Optional[Mapping[str, float]] = None) -> dict:
    """Minutes a default-dose event (1/2 inch) runs on each head type, rounded to 5.

    The package table gives 20 minutes (spray) and 60 (rotor); the owner table 30 and 80.
    """
    rates = HEAD_PRECIP_RATE_IN_PER_HR if rates is None else rates
    return {
        "spray": _round_to_5((EVENT_DEPTH_MIN_INCHES / rates["spray"]) * 60),
        "rotor": _round_to_5((EVENT_DEPTH_MIN_INCHES / rates["rotor"]) * 60),
    }


def _legal_max_events(restriction: Any) -> Optional[int]:
    """The legal ceiling from ``{"max_days_per_week": n}`` (``maxDaysPerWeek`` also works).

    None when there is no restriction or its ceiling is not a whole number of at least 0.
    A restriction without the key has no ceiling; one with ``None`` there means 0 (JavaScript
    ``Number(null)``), the same as the JavaScript code.
    """
    if not isinstance(restriction, Mapping):
        return None
    raw: Any = _NAN  # Number(undefined)
    if "max_days_per_week" in restriction:
        raw = restriction["max_days_per_week"]
    elif "maxDaysPerWeek" in restriction:
        raw = restriction["maxDaysPerWeek"]
    n = _js_number(raw)
    return int(n) if _is_integer(n) and n >= 0 else None


def build_week_plan(
    target_inches_per_week: Any = None,
    last_week_applied_inches: Any = None,
    last_week_rain_inches: Any = None,
    last_week_target_inches: Any = None,
    forecast_rain_inches: Any = None,
    season: str = "peak",
    restriction: Optional[Mapping[str, Any]] = None,
    run_minutes: Any = None,
    watering_days: Any = None,
    system_type: Any = None,
    explicit_inches_per_week: Any = None,
    rain_sensor: bool = False,
    rain_known: bool = True,
    prior_week_events: Any = None,
    rain_only_carryover: bool = False,
    rates: Optional[Mapping[str, float]] = None,
) -> dict:
    """Decide this week's watering.

    Inputs: ``target_inches_per_week`` (this week's turf need, for example ET0 x Kc),
    last week's rain and irrigation, the 7-day ``forecast_rain_inches``, ``season``
    (``peak``, ``shoulder`` or ``cool``) and the CURRENT legal ``restriction``
    (``{"max_days_per_week": 1}``; None means no plan). ``run_minutes``,
    ``watering_days`` and ``system_type`` size the minutes; ``rain_sensor`` and
    ``rain_only_carryover`` carry only observed rain; ``prior_week_events`` is last
    week's event count (cool-season cadence).

    ``action`` of the returned dict is ``unavailable`` (no legal policy or no target),
    ``hold`` (skip turf watering this week) or ``run``; a run with
    ``conditional_on_forecast`` true is for a week when at least 1/2 inch of rain is
    expected: leave it off, and run only if the rain does not come.
    ``reasons`` lists the codes behind the decision.
    """
    rates = HEAD_PRECIP_RATE_IN_PER_HR if rates is None else rates
    reasons: list = []
    legal_max_events = _legal_max_events(restriction)
    target = _finite_or_none(target_inches_per_week)
    seasonal_max = SEASONAL_MAX_EVENTS.get(season, SEASONAL_MAX_EVENTS["peak"])
    base = {
        "action": "unavailable",
        "events": 0,
        "depth_inches": None,
        "minutes_per_event": None,
        "rate_in_per_hr": None,
        "rate_source": None,
        "head_type": None,
        "permitted_days": None,  # never the customer's saved days: no assigned-day lane
        "legal_max_events": legal_max_events,
        "seasonal_max_events": seasonal_max,
        "target_inches": target,
        "carryover_inches": 0,
        "need_inches": None,
        "forecast_rain_inches": _finite_or_none(forecast_rain_inches),
        "conditional_on_forecast": False,
        "rain_sensor": rain_sensor is True,
        "season": season,
        "reasons": reasons,
        "confidence": "low",
    }
    if legal_max_events is None:
        reasons.append("restriction_policy_missing")
        return base
    if target is None or target < 0:
        reasons.append("target_missing")
        return base

    # Carryover: only a SURPLUS carries, only up to root-zone storage. With a rain
    # sensor the programmed irrigation is an upper bound, so only observed rain can
    # prove a surplus.
    rain_only = rain_sensor is True or rain_only_carryover is True
    applied = _finite_or_none(last_week_rain_inches if rain_only else last_week_applied_inches)
    last_target = _finite_or_none(last_week_target_inches)
    if last_target is None:
        last_target = target
    carryover = 0
    if applied is not None and applied > last_target:
        carryover = _round2(_clamp(applied - last_target, 0, ROOT_ZONE_STORAGE_INCHES))
        if carryover > 0:
            reasons.append("prior_week_rain_surplus" if rain_only else "prior_week_overwatered")
    need = _round2(max(0, target - carryover))
    if season == "cool":
        reasons.append("cool_season")

    rate = resolve_application_rate(explicit_inches_per_week, run_minutes, watering_days, system_type, rates=rates)
    forecast = base["forecast_rain_inches"]
    forecast_skips = forecast is not None and forecast >= RAIN_SKIP_INCHES
    if forecast_skips:
        reasons.append("forecast_rain")
    if forecast is None:
        reasons.append("forecast_unavailable")
    if not rain_known:
        reasons.append("rain_unknown")

    if not rain_known:
        confidence = "low"
    elif rate["rate_source"] == "measured" and forecast is not None:
        confidence = "high"
    else:
        confidence = "medium"

    max_events = min(legal_max_events, seasonal_max)

    # A "run" plan sized for the need, used as the plan and as the conditional fallback.
    def size_run(need_inches: float) -> dict:
        if max_events == 0:
            return {"events": 0, "depth_inches": None, "minutes_per_event": None}
        events = _clamp(math.ceil(need_inches / EVENT_DEPTH_MAX_INCHES), 1, max_events)
        depth = _round2(_clamp(need_inches / events, EVENT_DEPTH_MIN_INCHES, EVENT_DEPTH_MAX_INCHES))
        # A MEASURED rate earns a whole-minute figure; a published default is an
        # estimate and rounds to 5.
        if rate["rate_in_per_hr"]:
            if rate["rate_source"] == "measured":
                minutes = max(1, _js_round((depth / rate["rate_in_per_hr"]) * 60))
            else:
                minutes = _round_to_5((depth / rate["rate_in_per_hr"]) * 60)
        else:
            minutes = None
        return {"events": events, "depth_inches": depth, "minutes_per_event": minutes}

    common = {**base, **rate, "carryover_inches": carryover, "need_inches": need, "confidence": confidence}

    # A legal ban wins over everything, checked BEFORE the low-need hold.
    if max_events == 0:
        reasons.append("restriction_prohibits")
        return {**common, "action": "hold", "events": 0, "fallback_minutes_per_event": None}
    # Cool season is "every 10-14 days if needed": a run last week means a hold this
    # week, unless 1/2 inch or more of observed rain last week says that run was skipped.
    last_rain = _finite_or_none(last_week_rain_inches)
    prior_events = _js_number(prior_week_events)
    if season == "cool" and prior_events > 0 and not (last_rain is not None and last_rain >= RAIN_SKIP_INCHES):
        reasons.append("cool_season_cadence")
        fallback = size_run(EVENT_DEPTH_MIN_INCHES)
        return {
            **common,
            "action": "hold",
            "events": 0,
            "depth_inches": None,
            "minutes_per_event": None,
            "fallback_minutes_per_event": fallback["minutes_per_event"],
        }
    if need < HOLD_BELOW_INCHES:
        reasons.append("need_below_event_minimum")
        # The wilt-override cycle the copy offers is one default-dose event.
        fallback = size_run(EVENT_DEPTH_MIN_INCHES)
        return {
            **common,
            "action": "hold",
            "events": 0,
            "depth_inches": None,
            "minutes_per_event": None,
            "fallback_minutes_per_event": fallback["minutes_per_event"],
        }
    run = size_run(need)
    if need > run["events"] * EVENT_DEPTH_MAX_INCHES:
        reasons.append("restriction_limited" if legal_max_events <= seasonal_max else "season_limited")
    return {
        **common,
        **run,
        "action": "run",
        "conditional_on_forecast": forecast_skips,
        "fallback_minutes_per_event": run["minutes_per_event"],
    }
