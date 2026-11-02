"""Waves Lawn Tools: Florida lawn-watering math and a client for the free Waves public API.

https://github.com/wavespestcontrolfl/waves-lawn-tools
"""

from . import explore
from .api import (
    BASE_URL,
    WavesApiError,
    get_pest_forecast,
    get_pest_forecast_locations,
    get_pest_pressure_index,
    get_watering_plan,
    get_yard_calendar,
)
from .irrigation import (
    DAY_ALIASES,
    DAY_KEYS,
    HEAD_LABELS,
    HEAD_PRECIP_RATE_IN_PER_HR,
    MAX_INCHES_PER_WEEK,
    MAX_RUN_MINUTES,
    OWNER_HEAD_RATE_IN_PER_HR,
    OWNER_MINUTES_PER_QUARTER_INCH,
    WEEK_PLAN_CONSTANTS,
    build_week_plan,
    default_event_minutes,
    derive_irrigation_inches_per_week,
    describe_runtime_basis,
    normalize_runtime_inputs,
    resolve_application_rate,
)

__version__ = "1.2.0"

__all__ = [
    "BASE_URL",
    "DAY_ALIASES",
    "DAY_KEYS",
    "HEAD_LABELS",
    "HEAD_PRECIP_RATE_IN_PER_HR",
    "MAX_INCHES_PER_WEEK",
    "MAX_RUN_MINUTES",
    "OWNER_HEAD_RATE_IN_PER_HR",
    "OWNER_MINUTES_PER_QUARTER_INCH",
    "WEEK_PLAN_CONSTANTS",
    "WavesApiError",
    "__version__",
    "build_week_plan",
    "default_event_minutes",
    "derive_irrigation_inches_per_week",
    "describe_runtime_basis",
    "explore",
    "get_pest_forecast",
    "get_pest_forecast_locations",
    "get_pest_pressure_index",
    "get_watering_plan",
    "get_yard_calendar",
    "normalize_runtime_inputs",
    "resolve_application_rate",
]
