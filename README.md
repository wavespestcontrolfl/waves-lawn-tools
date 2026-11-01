# Waves Lawn Tools

Free, open-source lawn-watering math for Florida lawns, from
[Waves Pest Control & Lawn Care](https://www.wavespestcontrol.com/) in Southwest Florida.

- **Try it:** the free [Lawn Watering Calculator](https://www.wavespestcontrol.com/tools/lawn-watering-calculator/) runs on this code.
- **Use the data:** a free public API with no key and open CORS. See [docs/public-api.md](docs/public-api.md).
- **Embed it:** a copy-paste widget and a Home Assistant setup are on the [calculator page](https://www.wavespestcontrol.com/tools/lawn-watering-calculator/#embed).

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

## Sources

- UF/IFAS AE451, *Basic Repairs and Maintenance for Home Landscape Irrigation Systems*, and
  ENH9, *Watering Your Florida Lawn*: typical spray and rotor application rates
- UF/IFAS guidance to apply ½ to ¾ inch per watering, deep and infrequent
- The weekly need you pass in can come from reference evapotranspiration (FAO-56 ET0)
  times a turfgrass crop coefficient, which is how the calculator sizes it

## Run the tests

```sh
npm test
```

## Cite

See [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button for it.

## License

[MIT](LICENSE) © 2026 Waves Pest Control, LLC. Built and maintained by
[Waves Pest Control & Lawn Care](https://www.wavespestcontrol.com/), Lakewood Ranch, Florida.
