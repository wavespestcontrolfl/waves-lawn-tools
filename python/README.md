# waves-lawn-tools (Python)

Free, open-source lawn-watering math for Florida lawns, and a client for the free Waves
public API, from [Waves Pest Control & Lawn Care](https://www.wavespestcontrol.com/) in
Southwest Florida. No dependencies. Python 3.10 or newer.

- **Try it:** the free [Lawn Watering Calculator](https://www.wavespestcontrol.com/tools/lawn-watering-calculator/) runs on this math.
- **Use the data:** a free public API with no key. See the [API docs](https://github.com/wavespestcontrolfl/waves-lawn-tools/blob/main/docs/public-api.md).
- **Same code in JavaScript:** [waves-lawn-tools on GitHub](https://github.com/wavespestcontrolfl/waves-lawn-tools). The Python math is a port of the JavaScript file, and the tests check that every output matches.

## Install

```sh
pip install waves-lawn-tools
```

## Watering math

```python
from waves_lawn_tools import derive_irrigation_inches_per_week, build_week_plan

derive_irrigation_inches_per_week(run_minutes=20, watering_days=["Sat"], system_type="spray")
# {'inches_per_week': 0.5, 'run_minutes': 20, 'runs_per_week': 1, 'head_type': 'spray',
#  'rate_in_per_hr': 1.5, 'reason': None}

build_week_plan(
    target_inches_per_week=0.75,          # this week's turf need (for example ET0 x crop coefficient)
    last_week_rain_inches=0.2,            # measured rain over the last 7 days
    forecast_rain_inches=0,               # this week's forecast total
    season="peak",                        # "peak" | "shoulder" | "cool"
    restriction={"max_days_per_week": 1}, # the legal ceiling where you are; None = no plan
    system_type=["spray"],
    rain_known=True,
    rain_only_carryover=True,
)
# {'action': 'run', 'events': 1, 'depth_inches': 0.75, 'minutes_per_event': 30,
#  'legal_max_events': 1, 'reasons': [], ...}
```

It uses the University of Florida (UF/IFAS) typical rates: about 1.5 inches an hour for
spray heads and 0.5 for rotors. `action` is `run`, `hold` (skip turf watering this week) or
`unavailable` (no legal policy or no target). It declines instead of guessing: drip zones
water beds, not turf, so they get no lawn figure, and with no legal watering policy it
returns no plan rather than invent a limit.

Results are plain dicts with snake_case keys. Numbers follow the JavaScript rules where they
differ from Python (a half rounds up, like `Math.round`), so Python and JavaScript give the
same answer for the same input.

## Call the public API

```python
from waves_lawn_tools import (
    get_watering_plan, get_pest_forecast, get_yard_calendar, get_pest_pressure_index,
)

plan = get_watering_plan(zip="34205", head="spray", minutes=20)
plan["plan"]["action"]       # 'run', 'hold', 'need_only' or 'unavailable'
plan["text"]["headline"]     # a one-line answer for people

forecast = get_pest_forecast(location="bradenton-fl")
[f'{p["label"]}: {p["level"]}' for p in forecast["pests"]]

calendar = get_yard_calendar(month=11, grass="sta")

index = get_pest_pressure_index()                 # a dict
csv_text = get_pest_pressure_index(format="csv")  # the same table as CSV text
```

`get_pest_forecast_locations()` lists the city slugs. An error answer raises
`WavesApiError` with the HTTP `status`, the API's `code` (for example `unsupported_zip`) and
`message`. A network failure raises the usual `urllib.error.URLError`. Every call takes
`base_url=`, `opener=` and `timeout=` options. Please cache answers: the data changes a few
times a day at most, and the API allows 120 requests in 15 minutes from one address.

### Pest Pressure Index

`get_pest_pressure_index()` returns county averages of the pest-activity rating (0 None to
5 High) that Waves technicians record at completed service visits. Only groups with 20 or
more visits are listed. It is not a survey and not a forecast. The data is licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): credit it with the `citation`
text in the answer. Page: [Pest Pressure Index](https://www.wavespestcontrol.com/pest-pressure-index/).

### Tables for an app

`waves_lawn_tools.explore` turns the answers into rows for a table or a chart
(`pest_forecast_rows`, `yard_calendar_rows`, `pressure_index_rows`, `watering_plan_facts`,
`friendly_error`). The [Southwest Florida Lawn & Pest Explorer](https://github.com/wavespestcontrolfl/waves-lawn-tools/tree/main/apps/streamlit)
Streamlit app is built on them.

## Sources

- UF/IFAS AE451, *Basic Repairs and Maintenance for Home Landscape Irrigation Systems*, and
  ENH9, *Watering Your Florida Lawn*: typical spray and rotor application rates
- UF/IFAS guidance to apply 1/2 to 3/4 inch per watering, deep and infrequent

## Cite

See [CITATION.cff](https://github.com/wavespestcontrolfl/waves-lawn-tools/blob/main/CITATION.cff).
To cite the Pest Pressure Index data, use the `citation` field in the answer.

## License

[MIT](https://github.com/wavespestcontrolfl/waves-lawn-tools/blob/main/LICENSE) © 2026 Waves Pest Control, LLC.
