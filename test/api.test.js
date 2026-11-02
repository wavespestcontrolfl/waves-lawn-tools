'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('../src/api.js');
const pkg = require('../index.js');

function fakeFetch(status, body) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => (typeof body === 'string' ? JSON.parse(body) : body),
      text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
    };
  };
  fn.calls = calls;
  return fn;
}

test('getWateringPlan sends only the parameters given, a boolean sensor as 1/0', async () => {
  const fetch = fakeFetch(200, { plan: { action: 'run' } });
  const body = await api.getWateringPlan({ zip: '34205', head: 'spray', minutes: 20, sensor: true, grass: undefined }, { fetch });
  assert.equal(body.plan.action, 'run');
  const url = new URL(fetch.calls[0].url);
  assert.equal(url.origin + url.pathname, 'https://portal.wavespestcontrol.com/api/public/watering-plan');
  assert.deepEqual(Object.fromEntries(url.searchParams), { zip: '34205', head: 'spray', minutes: '20', sensor: '1' });
  assert.equal(fetch.calls[0].init.headers.accept, 'application/json');
});

test('getPestForecastLocations returns the list itself', async () => {
  const fetch = fakeFetch(200, { locations: [{ slug: 'bradenton-fl', label: 'Bradenton, FL' }] });
  const list = await api.getPestForecastLocations({ fetch });
  assert.equal(list[0].slug, 'bradenton-fl');
  assert.equal(new URL(fetch.calls[0].url).pathname, '/api/public/pest-forecast/locations');
});

test('getPestForecast and getYardCalendar hit their paths with their parameters', async () => {
  const fetch = fakeFetch(200, {});
  await api.getPestForecast({ location: 'venice-fl' }, { fetch });
  await api.getYardCalendar({ month: 11, grass: 'sta' }, { fetch, baseUrl: 'http://localhost:3000' });
  assert.equal(fetch.calls[0].url, 'https://portal.wavespestcontrol.com/api/public/pest-forecast?location=venice-fl');
  assert.equal(fetch.calls[1].url, 'http://localhost:3000/api/public/yard-calendar?month=11&grass=sta');
});

test('getPestPressureIndex asks for JSON by default and for CSV text on request', async () => {
  const json = fakeFetch(200, { name: 'Waves Pest Pressure Index', min_visits: 20, groups: [] });
  const body = await api.getPestPressureIndex({}, { fetch: json });
  assert.equal(body.min_visits, 20);
  assert.equal(json.calls[0].url, 'https://portal.wavespestcontrol.com/api/public/pest-pressure-index');
  assert.equal(json.calls[0].init.headers.accept, 'application/json');

  const csvText = 'county,service_line,visits,average,median,window_start,window_end\nManatee,pest,54,2.2,1.5,2026-09-24,2026-11-01\n';
  const csv = fakeFetch(200, csvText);
  assert.equal(await api.getPestPressureIndex({ format: 'csv' }, { fetch: csv }), csvText);
  assert.equal(csv.calls[0].url, 'https://portal.wavespestcontrol.com/api/public/pest-pressure-index?format=csv');
  assert.equal(csv.calls[0].init.headers.accept, 'text/csv');

  await assert.rejects(async () => api.getPestPressureIndex({ format: 'xml' }, { fetch: json }), RangeError);
});

test('an error answer throws WavesApiError with the status and the API code', async () => {
  const fetch = fakeFetch(400, { error: 'unsupported_zip', message: 'That ZIP code is not in a supported Florida area.' });
  await assert.rejects(api.getWateringPlan({ zip: '99999' }, { fetch }), (err) => {
    assert.ok(err instanceof api.WavesApiError);
    assert.equal(err.status, 400);
    assert.equal(err.code, 'unsupported_zip');
    assert.match(err.message, /not in a supported Florida area/);
    return true;
  });
});

test('the package root exports the watering math and the client together', () => {
  assert.equal(typeof pkg.buildWeekPlan, 'function');
  assert.equal(typeof pkg.deriveIrrigationInchesPerWeek, 'function');
  assert.equal(typeof pkg.getWateringPlan, 'function');
  assert.equal(typeof pkg.getPestPressureIndex, 'function');
  assert.equal(pkg.BASE_URL, 'https://portal.wavespestcontrol.com');
});
