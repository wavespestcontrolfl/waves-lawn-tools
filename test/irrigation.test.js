'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const w = require('../src/irrigation.js');

test('20 minutes once a week on spray heads is half an inch', () => {
  const r = w.deriveIrrigationInchesPerWeek({ runMinutes: 20, wateringDays: ['Sat'], systemType: 'spray' });
  assert.equal(r.inchesPerWeek, 0.5);
  assert.equal(r.rateInPerHr, 1.5);
  assert.equal(r.reason, null);
});

test('60 minutes twice a week on rotors is one inch', () => {
  const r = w.deriveIrrigationInchesPerWeek({ runMinutes: 60, wateringDays: ['Tue', 'Sat'], systemType: 'rotor' });
  assert.equal(r.inchesPerWeek, 1);
  assert.equal(r.runsPerWeek, 2);
});

test('drip waters beds, not turf, so it declines instead of guessing', () => {
  const r = w.deriveIrrigationInchesPerWeek({ runMinutes: 20, wateringDays: ['Sat'], systemType: 'drip' });
  assert.equal(r.inchesPerWeek, null);
  assert.equal(r.reason, 'drip_only');
});

test('a dry week under a one-day limit: one watering', () => {
  const p = w.buildWeekPlan({
    targetInchesPerWeek: 0.75, lastWeekRainInches: 0.2, forecastRainInches: 0, season: 'peak',
    restriction: { maxDaysPerWeek: 1 }, systemType: ['spray'], rainKnown: true, rainOnlyCarryover: true,
  });
  assert.equal(p.action, 'run');
  assert.equal(p.events, 1);
  assert.equal(p.legalMaxEvents, 1);
});

test('a soaked week carries over and holds the watering', () => {
  const p = w.buildWeekPlan({
    targetInchesPerWeek: 0.75, lastWeekRainInches: 2.4, lastWeekTargetInches: 0.75, forecastRainInches: 0.1,
    season: 'peak', restriction: { maxDaysPerWeek: 1 }, systemType: ['spray'], rainKnown: true, rainOnlyCarryover: true,
  });
  assert.equal(p.action, 'hold');
  assert.equal(p.events, 0);
  assert.ok(p.reasons.includes('prior_week_rain_surplus'));
});

test('no legal watering policy means no plan, never an invented limit', () => {
  const p = w.buildWeekPlan({ targetInchesPerWeek: 0.75, season: 'peak', restriction: null });
  assert.equal(p.action, 'unavailable');
  assert.deepEqual(p.reasons, ['restriction_policy_missing']);
});

test('default minutes for a half-inch watering', () => {
  assert.deepEqual(w.defaultEventMinutes(), { spray: 20, rotor: 60 });
  assert.deepEqual(w.defaultEventMinutes(w.OWNER_HEAD_RATE_IN_PER_HR), { spray: 30, rotor: 80 });
});
