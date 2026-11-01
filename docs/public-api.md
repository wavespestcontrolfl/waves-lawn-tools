# Waves public API

Free, read-only JSON endpoints from [Waves Pest Control](https://www.wavespestcontrol.com/).
No key, no sign-up. CORS is open (`Access-Control-Allow-Origin: *`), so a browser page on
any site can call them. Please cache responses: they carry `Cache-Control` headers, and
the data changes a few times a day at most.

Base URL: `https://portal.wavespestcontrol.com`

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

## MCP server (for AI agents)

`https://portal.wavespestcontrol.com/api/public/mcp` is a public, read-only MCP server
(streamable HTTP, no authentication) with the Waves service catalog, published price
ranges, service areas and quote instructions. It is listed in the official MCP Registry
as `com.wavespestcontrol/pest-control`.
