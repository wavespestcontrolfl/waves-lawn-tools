"""Waves Lawn Tools: waves_lawn_tools.api

A small client for the free Waves public API (docs/public-api.md, docs/openapi.json).
No key and no sign-up. Standard library only (``urllib``). It mirrors ``src/api.js``.

Please cache answers: they carry ``Cache-Control`` headers and the data changes a few
times a day at most. The API allows 120 requests in 15 minutes from one address.

MIT License. Copyright (c) 2026 Waves Pest Control, LLC.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Mapping, Optional

BASE_URL = "https://portal.wavespestcontrol.com"

DEFAULT_TIMEOUT = 20.0

# Cloudflare sits in front of the API and can refuse the stock "Python-urllib" agent.
USER_AGENT = "waves-lawn-tools-python/1.2.0 (+https://github.com/wavespestcontrolfl/waves-lawn-tools)"

__all__ = [
    "BASE_URL",
    "WavesApiError",
    "get_pest_forecast",
    "get_pest_forecast_locations",
    "get_pest_pressure_index",
    "get_watering_plan",
    "get_yard_calendar",
]


class WavesApiError(Exception):
    """The API answered with an error status.

    ``status`` is the HTTP status, ``code`` the API's error code (for example
    ``unsupported_zip``, or None), ``message`` the human text.
    """

    def __init__(self, status: int, code: Optional[str] = None, message: Optional[str] = None) -> None:
        self.status = status
        self.code = code
        self.message = message or code or f"Waves API answered {status}"
        super().__init__(self.message)

    @classmethod
    def from_body(cls, status: int, body: Any) -> "WavesApiError":
        """Build the error from a decoded JSON answer (any shape; None is fine)."""
        if isinstance(body, Mapping):
            code = body.get("error") or None
            message = body.get("message") or body.get("error") or None
            return cls(status, code if isinstance(code, str) else None, message if isinstance(message, str) else None)
        return cls(status)

    def __repr__(self) -> str:
        return f"WavesApiError(status={self.status!r}, code={self.code!r}, message={self.message!r})"


def _param_text(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _build_url(path: str, params: Mapping[str, Any], base_url: str) -> str:
    url = urllib.parse.urljoin(base_url, path)
    query = [(k, _param_text(v)) for k, v in params.items() if v is not None and v != ""]
    return url + ("?" + urllib.parse.urlencode(query) if query else "")


def _read_text(response: Any) -> str:
    data = response.read()
    return data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else str(data)


def _decode_json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


def _get(
    path: str,
    params: Mapping[str, Any],
    *,
    base_url: str = BASE_URL,
    opener: Any = None,
    timeout: float = DEFAULT_TIMEOUT,
    accept: str = "application/json",
) -> str:
    """GET and return the body text; raise WavesApiError for an error status."""
    url = _build_url(path, params, base_url)
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    opener = opener if opener is not None else urllib.request.build_opener()
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as err:
        try:
            body = _decode_json(_read_text(err))
        finally:
            err.close()
        raise WavesApiError.from_body(err.code, body) from None
    try:
        status = getattr(response, "status", None) or response.getcode()
        text = _read_text(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    if status is not None and not 200 <= status < 300:
        raise WavesApiError.from_body(status, _decode_json(text))
    return text


def _get_json(path: str, params: Mapping[str, Any], **options: Any) -> Any:
    return _decode_json(_get(path, params, **options))


def get_watering_plan(
    location: Optional[str] = None,
    zip: Optional[str] = None,  # noqa: A002  (the API's own parameter name)
    grass: Optional[str] = None,
    head: Optional[str] = None,
    minutes: Optional[int] = None,
    sensor: Optional[bool] = None,
    **options: Any,
) -> Dict[str, Any]:
    """This week's lawn watering plan. Pass ``location`` (a city slug) or ``zip``.

    ``grass``: st_augustine, zoysia, bahia, bermuda or unknown. ``head``: spray or rotor.
    ``minutes``: current minutes per zone (1 to 240). ``sensor``: True if there is a rain
    sensor. ``options``: ``base_url``, ``opener``, ``timeout``.
    """
    params = {"location": location, "zip": zip, "grass": grass, "head": head, "minutes": minutes, "sensor": sensor}
    return _get_json("/api/public/watering-plan", params, **options)


def get_pest_forecast_locations(**options: Any) -> List[Dict[str, Any]]:
    """The supported Florida cities: ``[{"slug", "label", "region", "county"}, ...]``."""
    body = _get_json("/api/public/pest-forecast/locations", {}, **options)
    return body["locations"]


def get_pest_forecast(location: Optional[str] = None, zip: Optional[str] = None, **options: Any) -> Dict[str, Any]:  # noqa: A002
    """This month's pest pressure forecast for a city slug or a ZIP.

    Unknown ones fall back to Southwest Florida. It is a seasonal, weather-based model,
    not a measurement.
    """
    return _get_json("/api/public/pest-forecast", {"location": location, "zip": zip}, **options)


def get_yard_calendar(month: Optional[int] = None, grass: Optional[str] = None, **options: Any) -> Dict[str, Any]:
    """The yard pressure calendar for a month (1 to 12) and grass (all, sta, bah, zoy, ber)."""
    return _get_json("/api/public/yard-calendar", {"month": month, "grass": grass}, **options)


def get_pest_pressure_index(format: str = "json", **options: Any) -> Any:  # noqa: A002
    """The Southwest Florida Pest Pressure Index.

    County averages of the pest-activity rating (0 to 5) that Waves technicians record at
    completed service visits. Only groups with 20 or more visits are listed. The data is
    licensed CC BY 4.0; page: https://www.wavespestcontrol.com/pest-pressure-index/.

    ``format="json"`` (default) returns a dict; ``format="csv"`` returns the CSV text.
    """
    if format not in ("json", "csv"):
        raise ValueError("format must be 'json' or 'csv'")
    path = "/api/public/pest-pressure-index"
    if format == "csv":
        return _get(path, {"format": "csv"}, accept="text/csv", **options)
    return _get_json(path, {}, **options)
