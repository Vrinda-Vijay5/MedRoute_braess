"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { assess, accepts } = require("../src/guard");
const good = { baselineMs: 20, candidateMs: 30, samples: 10, expectedSamples: 10, ageSeconds: 1, now: 100 };
test("measured shortcut decision: harmful, beneficial, neutral", () => {
  assert.equal(assess(good).route, "baseline");
  assert.equal(assess({ ...good, candidateMs: 10 }).route, "shortcut");
  assert.equal(assess({ ...good, candidateMs: 20 }).verdict, "neutral");
});
test("missing, invalid, incomplete, stale telemetry fails safe", () => {
  for (const x of [{ ...good, samples: 1 }, { ...good, ageSeconds: 10 }, { ...good, candidateMs: NaN }, { ...good, baselineMs: 0 }]) {
    assert.equal(assess(x).verdict, "inconclusive"); assert.equal(assess(x).route, "baseline");
  }
});
test("acceptance distinguishes infrastructure failure and live prevention", () => {
  assert.equal(accepts({ infrastructureOk: false }).status, "infrastructure_failure");
  assert.equal(accepts({ infrastructureOk: true, baseline: 20, shortcut: 30, prevented: 20, expectedRoute: "long", actualRoute: "long" }).accepted, true);
  assert.equal(accepts({ infrastructureOk: true, baseline: 20, shortcut: 30, prevented: 30, expectedRoute: "long", actualRoute: "shortcut" }).accepted, false);
});
