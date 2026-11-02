'use strict';

// A small client for the free Waves public API (docs/public-api.md, docs/openapi.json).
// No key and no sign-up. Uses the global fetch: Node 18 or newer, or any browser.

const BASE_URL = 'https://portal.wavespestcontrol.com';

class WavesApiError extends Error {
  constructor(status, body) {
    super((body && (body.message || body.error)) || `Waves API answered ${status}`);
    this.name = 'WavesApiError';
    this.status = status;
    this.code = (body && body.error) || null;
  }
}

async function getJson(path, params, options = {}) {
  const { baseUrl = BASE_URL, fetch: fetchImpl = globalThis.fetch, signal } = options;
  if (typeof fetchImpl !== 'function') throw new TypeError('No fetch: use Node 18 or newer, or pass { fetch }.');
  const url = new URL(path, baseUrl);
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    url.searchParams.set(key, typeof value === 'boolean' ? (value ? '1' : '0') : String(value));
  }
  const res = await fetchImpl(url.toString(), { headers: { accept: 'application/json' }, signal });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new WavesApiError(res.status, body);
  return body;
}

/**
 * This week's lawn watering plan. Pass `location` (a city slug) or `zip`.
 * grass: st_augustine | zoysia | bahia | bermuda | unknown; head: spray | rotor;
 * minutes: current minutes per zone (1-240); sensor: true if there is a rain sensor.
 */
function getWateringPlan({ location, zip, grass, head, minutes, sensor } = {}, options) {
  return getJson('/api/public/watering-plan', { location, zip, grass, head, minutes, sensor }, options);
}

/** The supported Florida cities: [{ slug, label, region, county }]. */
async function getPestForecastLocations(options) {
  const body = await getJson('/api/public/pest-forecast/locations', {}, options);
  return body.locations;
}

/** This month's pest pressure forecast for a city slug or a ZIP (unknown ones fall back to Southwest Florida). */
function getPestForecast({ location, zip } = {}, options) {
  return getJson('/api/public/pest-forecast', { location, zip }, options);
}

/** The yard pressure calendar for a month (1-12) and grass (all | sta | bah | zoy | ber). */
function getYardCalendar({ month, grass } = {}, options) {
  return getJson('/api/public/yard-calendar', { month, grass }, options);
}

module.exports = {
  BASE_URL,
  WavesApiError,
  getWateringPlan,
  getPestForecastLocations,
  getPestForecast,
  getYardCalendar,
};
