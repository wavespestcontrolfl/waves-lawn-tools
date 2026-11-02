'use strict';

// Writes irrigation_cases.json: inputs and the exact outputs of src/irrigation.js.
// The Python tests (python/tests/test_parity.py) must reproduce every output.
//
//   node python/tests/fixtures/make_fixtures.js
//
// The inputs are synthetic. No customer data. A fixed pseudo-random generator picks the
// combinations, so a rerun writes the same file unless src/irrigation.js changed.

const fs = require('node:fs');
const path = require('node:path');
const w = require('../../../src/irrigation.js');

// --- deterministic pseudo-random (mulberry32) --------------------------------------
let seed = 20261102;
function rand() {
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const pick = (list) => list[Math.floor(rand() * list.length)];

// A marker for "leave this key out" (JavaScript undefined). JSON has no undefined.
const OMIT = Symbol('omit');
function clean(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj)) if (v !== OMIT) out[k] = v;
  return out;
}

const cases = [];
function add(fn, args) {
  const result = w[fn](...args.map((a) => (a && typeof a === 'object' && !Array.isArray(a) ? JSON.parse(JSON.stringify(a)) : a)));
  assertPlainNumbers(result, fn, args);
  cases.push({ fn, args, result: JSON.parse(JSON.stringify(result)) });
}
function assertPlainNumbers(value, fn, args) {
  if (typeof value === 'number' && !Number.isFinite(value)) {
    throw new Error(`${fn} gave ${value} for ${JSON.stringify(args)}; leave that input out of the fixtures`);
  }
  if (typeof value === 'function') throw new Error(`${fn} gave a function for ${JSON.stringify(args)}`);
  if (value && typeof value === 'object') for (const v of Object.values(value)) assertPlainNumbers(v, fn, args);
}

// --- inputs for the runtime math -----------------------------------------------------
const MINUTES = [
  OMIT, null, 0, -5, 1, 7, 15, 20, 20.4, 20.5, 20.6, 21, 25, 30, 45, 59.5, 60, 90, 120, 239.5, 240, 240.4, 240.5, 241, 1000000,
  '45', ' 30 ', '0x10', '1e1', 'abc', '', 'Infinity', true, false, [20], ['20'], [1, 2], [],
];
const DAYS = [
  OMIT, null, [], ['Sat'], ['Mon', 'Wed', 'Fri'], ['Tue', 'Sat'], ['monday', 'TUESDAY', ' Thurs '], ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
  ['Sun', 'Sat', 'Mon'], '["Mon","Thu"]', '["Mon"', 'Sat', 'monthly', ['sunny'], '[]', ['Mon', 'mon', 'Monday'], ['Mon', 5, null, ''], [['Mon']],
  ['Weds', 'Fri', 'Saturday'], '   ', '{"a":1}', 7,
];
const HEADS = [
  OMIT, null, 'spray', ['spray'], ['rotor'], ['drip'], ['spray', 'rotor'], ['spray', 'drip'], ['drip', 'rotor'], [' SPRAY ', 'spray'],
  [], 'sprinkler', ['foo'], '["rotor"]', '"spray"', 'rotor', ['Rotor'], ['drip', 'drip'], '[]', ['spray', ''],
];
const RATES = [
  OMIT, { spray: 2, rotor: 0.3 }, { spray: 1, rotor: 0.375 }, { spray: 1.5 }, { spray: 1.5, rotor: 0.5, micro: 0.25 }, { spray: 0.1, rotor: 4 },
];

// every minutes value once, with a common schedule; every day and head shape once
for (const m of MINUTES) add('deriveIrrigationInchesPerWeek', [clean({ runMinutes: m, wateringDays: ['Sat'], systemType: 'spray' })]);
for (const d of DAYS) add('deriveIrrigationInchesPerWeek', [clean({ runMinutes: 30, wateringDays: d, systemType: ['rotor'] })]);
for (const h of HEADS) add('deriveIrrigationInchesPerWeek', [clean({ runMinutes: 30, wateringDays: ['Tue', 'Fri'], systemType: h })]);
// a seeded sample across all three
for (let i = 0; i < 260; i += 1) {
  add('deriveIrrigationInchesPerWeek', [clean({ runMinutes: pick(MINUTES), wateringDays: pick(DAYS), systemType: pick(HEADS) })]);
}
// tie cases: minutes x days odd on spray (x2.5 per hundredth), and thirds
for (const m of [1, 3, 9, 11, 13, 17, 19, 21, 23, 27, 33, 41, 99, 101]) {
  for (const n of [1, 3, 5, 7]) {
    add('deriveIrrigationInchesPerWeek', [{ runMinutes: m, wateringDays: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].slice(0, n), systemType: ['spray'] }]);
  }
}
// other rate tables and ignoreDrip
for (const r of RATES) {
  for (const h of [['spray'], ['rotor'], ['micro'], ['drip'], ['spray', 'drip']]) {
    add('deriveIrrigationInchesPerWeek', [{ runMinutes: 25, wateringDays: ['Mon', 'Thu'], systemType: h }, clean({ rates: r })]);
  }
}
for (const h of [['spray'], ['drip'], ['spray', 'drip'], ['rotor', 'drip'], ['spray', 'rotor', 'drip'], []]) {
  for (const ignoreDrip of [true, false]) {
    add('deriveIrrigationInchesPerWeek', [{ runMinutes: 20, wateringDays: ['Sat'], systemType: h }, { ignoreDrip }]);
  }
}
add('deriveIrrigationInchesPerWeek', []);
add('deriveIrrigationInchesPerWeek', [{}]);

// describeRuntimeBasis takes a derived result
for (const [m, d, h] of [[20, ['Sat'], 'spray'], [20, ['Mon', 'Thu', 'Sat', 'Sun'], 'spray'], [60, ['Tue', 'Sat'], 'rotor'], [10, ['Mon', 'Tue'], 'drip']]) {
  const derived = w.deriveIrrigationInchesPerWeek({ runMinutes: m, wateringDays: d, systemType: h });
  add('describeRuntimeBasis', [derived]);
}
add('describeRuntimeBasis', [null]);
add('describeRuntimeBasis', [{ inchesPerWeek: 1, runsPerWeek: 3, runMinutes: 40, headType: 'micro' }]);

// normalizeRuntimeInputs
for (let i = 0; i < 40; i += 1) {
  add('normalizeRuntimeInputs', [clean({ runMinutes: pick(MINUTES), wateringDays: pick(DAYS), systemType: pick(HEADS) })]);
}
add('normalizeRuntimeInputs', []);

// resolveApplicationRate
const EXPLICIT = [OMIT, null, 0, -1, 0.1, 0.5, 1, 1.5, 3, 10, '2', 'x', ''];
for (let i = 0; i < 160; i += 1) {
  add('resolveApplicationRate', [
    clean({ explicitInchesPerWeek: pick(EXPLICIT), runMinutes: pick(MINUTES), wateringDays: pick(DAYS), systemType: pick(HEADS) }),
    clean({ rates: pick(RATES) }),
  ]);
}
// measured-rate edges: rate = inches / (minutes/60 x days)
for (const [inches, minutes] of [[0.5, 60], [0.2, 60], [0.19, 60], [4, 60], [4.05, 60], [1, 23], [0.75, 17], [2.5, 31], [1.25, 47]]) {
  add('resolveApplicationRate', [{ explicitInchesPerWeek: inches, runMinutes: minutes, wateringDays: ['Mon'], systemType: ['spray'] }]);
}
add('resolveApplicationRate', []);

// defaultEventMinutes
add('defaultEventMinutes', []);
add('defaultEventMinutes', [w.OWNER_HEAD_RATE_IN_PER_HR]);
add('defaultEventMinutes', [{ spray: 2, rotor: 0.3 }]);
add('defaultEventMinutes', [{ spray: 1.2, rotor: 0.45 }]);

// --- buildWeekPlan -------------------------------------------------------------------
const TARGET = [OMIT, null, 0, 0.3, 0.5, 0.75, 1, 1.4, 1.5, 1.6, 2.2, -1, '0.9', 'abc', ''];
const RESTRICTION = [
  OMIT, null, {}, { maxDaysPerWeek: 0 }, { maxDaysPerWeek: 1 }, { maxDaysPerWeek: 1 }, { maxDaysPerWeek: 2 }, { maxDaysPerWeek: 3 }, { maxDaysPerWeek: 7 },
  { maxDaysPerWeek: '2' }, { maxDaysPerWeek: 1.5 }, { maxDaysPerWeek: -1 }, { maxDaysPerWeek: null }, { maxDaysPerWeek: '' }, { label: 'x' }, 'x', 3,
];
const VALID_TARGET = [0, 0.3, 0.5, 0.75, 0.75, 1, 1.4, 1.5, 1.6, 2.2, '0.9'];
const VALID_RESTRICTION = [{ maxDaysPerWeek: 0 }, { maxDaysPerWeek: 1 }, { maxDaysPerWeek: 1 }, { maxDaysPerWeek: 2 }, { maxDaysPerWeek: 3 }, { maxDaysPerWeek: 7 }, { maxDaysPerWeek: '2' }, { maxDaysPerWeek: null }];
const SEASON = [OMIT, 'peak', 'shoulder', 'cool', 'winter', null];
const RAIN = [OMIT, null, 0, 0.2, 0.49, 0.5, 1, 1.3, 2.4, '1.2', 'x'];
const FORECAST = [OMIT, null, 0, 0.1, 0.49, 0.5, 0.6, 2];
const SYSTEM = [OMIT, null, ['spray'], ['rotor'], ['drip'], ['spray', 'rotor'], 'spray', ['micro']];
const PLAN_MINUTES = [OMIT, null, 10, 20, 21, 37, 45, 60, 240, 300, '25'];
const PLAN_DAYS = [OMIT, null, ['Sat'], ['Mon', 'Thu'], ['Mon', 'Wed', 'Fri'], '["Tue"]', []];
const PLAN_EXPLICIT = [OMIT, null, 0, 0.5, 1, 2, 3.5, 10];
const PRIOR = [OMIT, null, 0, 1, 2, '1'];
const FLAG = [OMIT, true, false, true, false, 'true', 1, null];
const PLAN_RATES = [OMIT, OMIT, OMIT, { spray: 1, rotor: 0.375 }, { spray: 2, rotor: 0.3 }];

// readable anchors first
const dry = { targetInchesPerWeek: 0.75, lastWeekRainInches: 0.2, forecastRainInches: 0, season: 'peak', restriction: { maxDaysPerWeek: 1 }, systemType: ['spray'], rainKnown: true, rainOnlyCarryover: true };
add('buildWeekPlan', [dry]);
add('buildWeekPlan', [{ ...dry, lastWeekRainInches: 2.4, lastWeekTargetInches: 0.75, forecastRainInches: 0.1 }]);
add('buildWeekPlan', [{ targetInchesPerWeek: 0.75, season: 'peak', restriction: null }]);
add('buildWeekPlan', [{ ...dry, restriction: { maxDaysPerWeek: 2 }, targetInchesPerWeek: 1.5, runMinutes: 20, wateringDays: ['Mon', 'Thu'], explicitInchesPerWeek: 1 }]);
add('buildWeekPlan', [{ ...dry, season: 'cool', priorWeekEvents: 1 }]);
add('buildWeekPlan', [{ ...dry, season: 'cool', priorWeekEvents: 1, lastWeekRainInches: 0.5 }]);
add('buildWeekPlan', [{ ...dry, forecastRainInches: 0.5 }]);
add('buildWeekPlan', [{ ...dry, rainKnown: false }]);
add('buildWeekPlan', [{ ...dry, restriction: { maxDaysPerWeek: 0 } }]);
add('buildWeekPlan', [{ ...dry, rates: w.OWNER_HEAD_RATE_IN_PER_HR }]);
add('buildWeekPlan', [{ ...dry, rainSensor: true, lastWeekAppliedInches: 3, lastWeekRainInches: 0.1 }]);
add('buildWeekPlan', [{}]);
add('buildWeekPlan', []);
// the seeded sample
for (let i = 0; i < 900; i += 1) {
  // 70% of the sample has a valid target and restriction, so the sizing code gets exercised
  const valid = rand() < 0.7;
  const restriction = valid ? pick(VALID_RESTRICTION) : pick(RESTRICTION);
  const input = clean({
    targetInchesPerWeek: valid ? pick(VALID_TARGET) : pick(TARGET),
    lastWeekAppliedInches: pick(RAIN),
    lastWeekRainInches: pick(RAIN),
    lastWeekTargetInches: pick(TARGET),
    forecastRainInches: pick(FORECAST),
    season: pick(SEASON),
    restriction,
    runMinutes: pick(PLAN_MINUTES),
    wateringDays: pick(PLAN_DAYS),
    systemType: pick(SYSTEM),
    explicitInchesPerWeek: pick(PLAN_EXPLICIT),
    rainSensor: pick(FLAG),
    rainKnown: pick(FLAG),
    priorWeekEvents: pick(PRIOR),
    rainOnlyCarryover: pick(FLAG),
    rates: pick(PLAN_RATES),
  });
  try {
    add('buildWeekPlan', [input]);
  } catch (err) {
    if (!/leave that input out/.test(err.message)) throw err;
  }
}

// --- constants ------------------------------------------------------------------------
const constants = {
  HEAD_PRECIP_RATE_IN_PER_HR: w.HEAD_PRECIP_RATE_IN_PER_HR,
  OWNER_MINUTES_PER_QUARTER_INCH: w.OWNER_MINUTES_PER_QUARTER_INCH,
  OWNER_HEAD_RATE_IN_PER_HR: w.OWNER_HEAD_RATE_IN_PER_HR,
  HEAD_LABELS: w.HEAD_LABELS,
  DAY_KEYS: w.DAY_KEYS,
  DAY_ALIASES: w.DAY_ALIASES,
  MAX_RUN_MINUTES: w.MAX_RUN_MINUTES,
  MAX_INCHES_PER_WEEK: w.MAX_INCHES_PER_WEEK,
  WEEK_PLAN_CONSTANTS: w.WEEK_PLAN_CONSTANTS,
};

const out = path.join(__dirname, 'irrigation_cases.json');
const lines = cases.map((c) => '    ' + JSON.stringify(c));
fs.writeFileSync(out, `{\n  "constants": ${JSON.stringify(constants)},\n  "cases": [\n${lines.join(',\n')}\n  ]\n}\n`);
console.log(`wrote ${cases.length} cases to ${path.relative(process.cwd(), out)}`);
