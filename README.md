# Waves Lawn Tools

Free, open-source lawn-watering math for Florida lawns, from
[Waves Pest Control & Lawn Care](https://www.wavespestcontrol.com/) in Southwest Florida.

- **Try it:** the free [Lawn Watering Calculator](https://www.wavespestcontrol.com/tools/lawn-watering-calculator/) runs on this code.
- **Use the data:** a free public API with no key and open CORS. See [docs/public-api.md](docs/public-api.md).
- **Embed it:** a copy-paste widget and a Home Assistant setup are on the [calculator page](https://www.wavespestcontrol.com/tools/lawn-watering-calculator/#embed).
- **Python:** the same math and API client on PyPI: `pip install waves-lawn-tools`. See [Python](#python).
- **Hugging Face:** the widget as a [Space](#hugging-face).

## What it does

`src/irrigation.js` is one dependency-free CommonJS file that answers two questions:

1. **How much water does my sprinkler put down?** It turns minutes per zone × watering
   days × head type into inches per week, using the University of Florida (UF/IFAS)
   typical rates: about 1.5 inches an hour for spray heads and 0.5 for rotors.
2. **How should I water this week?** It sizes the week from the turf's need, last week's
   measured rain, the week's forecast and the local watering limit, in half-inch to
   three-quarter-inch waterings.

It declines instead of guessing. Drip zones water beds, not turf, so they get no lawn
figure. With no legal watering policy, it returns no plan rather than invent a limit.

## Install

```sh
npm install github:wavespestcontrolfl/waves-lawn-tools
```

Or copy `src/irrigation.js` into your project. It needs Node 18 or newer, or any bundler.

## Use

```js
const { deriveIrrigationInchesPerWeek, buildWeekPlan } = require('waves-lawn-tools');

deriveIrrigationInchesPerWeek({ runMinutes: 20, wateringDays: ['Sat'], systemType: 'spray' });
// { inchesPerWeek: 0.5, runMinutes: 20, runsPerWeek: 1, headType: 'spray', rateInPerHr: 1.5, reason: null }

buildWeekPlan({
  targetInchesPerWeek: 0.75,        // this week's turf need (for example ET0 x crop coefficient)
  lastWeekRainInches: 0.2,          // measured rain over the last 7 days
  forecastRainInches: 0,            // this week's forecast total
  season: 'peak',                   // 'peak' | 'shoulder' | 'cool'
  restriction: { maxDaysPerWeek: 1 },   // the legal ceiling where you are; null = no plan
  systemType: ['spray'],
  rainKnown: true,
  rainOnlyCarryover: true,
});
// { action: 'run', events: 1, depthInches: 0.75, minutesPerEvent: 30, legalMaxEvents: 1, ... }
```

`action` is `run`, `hold` (skip turf watering this week) or `unavailable` (no legal policy
or no target). A soaked week carries up to half an inch of surplus into the next one.

## Call the public API

The package also has a small client for the free Waves public API (no key, open CORS).
It uses the global `fetch` of Node 18 or newer, or a browser.

```js
const { getWateringPlan, getPestForecast, getYardCalendar, getPestPressureIndex } = require('waves-lawn-tools');

const plan = await getWateringPlan({ zip: '34205', head: 'spray', minutes: 20 });
plan.plan.action;        // 'run', 'hold', 'need_only' or 'unavailable'
plan.text.headline;      // a one-line answer for people

const forecast = await getPestForecast({ location: 'bradenton-fl' });
forecast.pests.map((p) => `${p.label}: ${p.level}`);

const yard = await getYardCalendar({ month: 11, grass: 'sta' });

const index = await getPestPressureIndex();                  // county averages of technician pest ratings (CC BY 4.0)
const csv = await getPestPressureIndex({ format: 'csv' });   // the same table as CSV text
```

`getPestForecastLocations()` lists the city slugs. An error answer throws a `WavesApiError`
with the HTTP `status` and the API's `code` (for example `unsupported_zip`).

The endpoints are described in [docs/public-api.md](docs/public-api.md) and, as OpenAPI 3.0,
in [docs/openapi.json](docs/openapi.json). To try them in Postman, import
[docs/waves-public-api.postman_collection.json](docs/waves-public-api.postman_collection.json).

## Python

The same watering math and API client are on PyPI as
[`waves-lawn-tools`](https://pypi.org/project/waves-lawn-tools/), with no dependencies and
Python 3.9 or newer. The code is in [python/](python/).

```sh
pip install waves-lawn-tools
```

```python
from waves_lawn_tools import derive_irrigation_inches_per_week, get_watering_plan

derive_irrigation_inches_per_week(run_minutes=20, watering_days=["Sat"], system_type="spray")["inches_per_week"]  # 0.5
get_watering_plan(zip="34205", head="spray", minutes=20)["text"]["headline"]
```

The Python math is a port of `src/irrigation.js`. `python/tests/fixtures/make_fixtures.js`
runs the JavaScript over more than 1,500 inputs, and the Python tests must reproduce every
output exactly. [apps/streamlit](apps/streamlit) is a Streamlit app built on the package:
the Southwest Florida Lawn & Pest Explorer.

## Hugging Face

The calculator's embed widget runs as a static
[Hugging Face Space](https://huggingface.co/spaces/wavespestcontrol/florida-lawn-watering-calculator).
Its files are in [apps/huggingface-space](apps/huggingface-space).

## Sources

- UF/IFAS AE451, *Basic Repairs and Maintenance for Home Landscape Irrigation Systems*, and
  ENH9, *Watering Your Florida Lawn*: typical spray and rotor application rates
- UF/IFAS guidance to apply ½ to ¾ inch per watering, deep and infrequent
- The weekly need you pass in can come from reference evapotranspiration (FAO-56 ET0)
  times a turfgrass crop coefficient, which is how the calculator sizes it

## Run the tests

```sh
npm test                                                          # JavaScript
PYTHONPATH=python/src python3 -m unittest discover -s python/tests  # Python
```

## Cite

See [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button for it.

## License

[MIT](LICENSE) © 2026 Waves Pest Control, LLC. Built and maintained by
[Waves Pest Control & Lawn Care](https://www.wavespestcontrol.com/), Lakewood Ranch, Florida.
