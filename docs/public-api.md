# Waves public API

Free, read-only JSON endpoints from [Waves Pest Control](https://www.wavespestcontrol.com/).
No key, no sign-up. CORS is open (`Access-Control-Allow-Origin: *`), so a browser page on
any site can call them. Please cache responses: they carry `Cache-Control` headers, and
the data changes a few times a day at most.

Base URL: `https://portal.wavespestcontrol.com`

An OpenAPI 3.0 description of every endpoint below, with example responses, is in
[openapi.json](openapi.json).

## Lawn watering plan

`GET /api/public/watering-plan`

| Parameter | Required | Values |
|---|---|---|
| `location` | one of `location` or `zip` | a city slug from `/api/public/pest-forecast/locations`, for example `bradenton-fl` |
| `zip` | one of `location` or `zip` | a 5-digit Florida ZIP code |
| `grass` | no | `st_augustine`, `zoysia`, `bahia`, `bermuda`, `unknown` |
| `head` | no | `spray`, `rotor` |
| `minutes` | no | your current minutes per zone, 1 to 240 (used with `head`) |
| `sensor` | no | `1` if the system has a rain sensor, else `0` |

```sh
curl "https://portal.wavespestcontrol.com/api/public/watering-plan?location=bradenton-fl&head=spray"
```

Response keys: `location` (`slug`, `label`, `county`), `asOf`, `week` (`start`, `end`),
`rain` (`last7Inches`, `source`), `forecast` (`rainInches`, `et0Inches`) or `null`,
`need` (`targetInches`, `basis`, `netInches`), `plan` (`action`, `events`, `depthInches`,
`minutesPerEvent`, `conditionalOnForecast`, `legalMaxEvents`), `restriction` (`label`,
`maxDaysPerWeek`, `source`) or `null`, `rulesUrl`, `text` (`headline`, `action`, `notes`),
`landing`, `brand`, `disclaimer`.

- `plan.action` is `run`, `hold`, `need_only` or `unavailable`. `need_only` means we do not
  track a watering order for that county, so the answer is the lawn's need, not a schedule.
- Every answer links the county's water management district rules in `rulesUrl`. Local
  rules always come first.
- Errors: `400` for a bad or unsupported parameter (for example a ZIP outside Florida),
  `429` past 120 requests in 15 minutes from one address, `503` when weather data is down.

## Pest pressure forecast

- `GET /api/public/pest-forecast/locations`: the supported Florida cities (`slug`, `label`, `region`, `county`).
- `GET /api/public/pest-forecast?location=<slug>` (or `?zip=<zip>`): this month's modeled
  pest outlook for the city, with `weather`, `summary`, one entry per pest in `pests`
  (`key`, `label`, `score`, `baseline_comparison`, `level`, `trend`, ...), `attribution`
  and `disclaimer`. It is a seasonal and weather-based model, not a measurement.

An embeddable widget for it is on the
[Pest Pressure Forecast page](https://www.wavespestcontrol.com/tools/pest-pressure-forecast/).

## Yard pressure calendar

`GET /api/public/yard-calendar?month=11&grass=sta`: what is active in Southwest Florida yards
that month, derived from the Waves species catalog. Each entry in `items` is a
lawn pest, lawn disease, shrub or tree pest, or weed (`id`, `category`, `name`, `hosts`,
`level`, `levelLabel`, `trend`, `sign`, ...), with `levels`, its level for every month from
January to December. `planAhead` lists what to plan for now.

| Parameter | Required | Values |
|---|---|---|
| `month` | no | `1` to `12`; default: the current month (US Eastern) |
| `grass` | no | `all` (default), `sta` St. Augustine, `bah` Bahia, `zoy` Zoysia, `ber` Bermuda |

Any other value is a `400` (`invalid_month` or `invalid_grass`). The content changes once a
month, so cache it.

## Pest Pressure Index

`GET /api/public/pest-pressure-index`: county averages of the pest-activity rating that
Waves technicians record at completed service visits, on a scale from 0 (None) to 5 (High),
over the last few weeks. It is an average of technician ratings, not a survey and not a
forecast. A county and service line is listed only with **20 or more visits** in the window;
smaller groups are counted in `hidden_groups` and left out. Page:
[Pest Pressure Index](https://www.wavespestcontrol.com/pest-pressure-index/).

| Parameter | Required | Values |
|---|---|---|
| `format` | no | `json` (default) or `csv` (`text/csv`, one row per group) |

```sh
curl "https://portal.wavespestcontrol.com/api/public/pest-pressure-index"
curl "https://portal.wavespestcontrol.com/api/public/pest-pressure-index?format=csv"
```

```json
{
  "name": "Waves Pest Pressure Index",
  "region": "Southwest Florida",
  "window": {
    "start": "2026-09-24",
    "end": "2026-11-01",
    "days": 39
  },
  "scale": {
    "min": 0,
    "max": 5,
    "labels": {
      "0": "None",
      "1": "Very Low",
      "2": "Low",
      "3": "Moderate",
      "4": "Elevated",
      "5": "High"
    },
    "meaning": "Technician's on-site pest activity rating at a completed Waves service visit."
  },
  "min_visits": 20,
  "groups": [
    {
      "county": "Manatee",
      "service_line": "pest",
      "visits": 54,
      "average": 2.2,
      "median": 1.5
    }
  ],
  "hidden_groups": 1,
  "source": "Completed Waves Pest Control service visits rated by the technician on site. Not a survey and not a forecast.",
  "license": {
    "name": "CC BY 4.0",
    "url": "https://creativecommons.org/licenses/by/4.0/"
  },
  "citation": "Waves Pest Control. Southwest Florida Pest Pressure Index. https://www.wavespestcontrol.com/pest-pressure-index/",
  "page_url": "https://www.wavespestcontrol.com/pest-pressure-index/",
  "generated_at": "2026-11-02T07:51:36.600Z"
}
```

The CSV form (the columns add the window dates):

```csv
county,service_line,visits,average,median,window_start,window_end
Manatee,pest,54,2.2,1.5,2026-09-24,2026-11-01
```

Response keys: `name`, `region`, `window` (`start`, `end`, `days`), `scale` (`min`, `max`,
`labels`, `meaning`), `min_visits`, `groups` (`county`, `service_line`, `visits`, `average`,
`median`), `hidden_groups`, `source`, `license`, `citation`, `page_url`, `generated_at`.

- The data is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit it
  with the `citation` text and link `page_url`.
- Cache it: the answer carries `Cache-Control: public, max-age=3600`.
- Errors: `429` past 120 requests in 15 minutes from one address.

## MCP server (for AI agents)

`https://portal.wavespestcontrol.com/api/public/mcp` is a public, read-only MCP server
(streamable HTTP, no authentication) with the Waves service catalog, published price
ranges, service areas and quote instructions. It is listed in the official MCP Registry
as `com.wavespestcontrol/pest-control`.
