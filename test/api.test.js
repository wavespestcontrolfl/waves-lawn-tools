'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('../src/api.js');
const pkg = require('../index.js');

function fakeFetch(status, body) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, init });
    return { ok: status >= 200 && status < 300, status, json: async () => body };
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
  assert.equal(pkg.BASE_URL, 'https://portal.wavespestcontrol.com');
});
