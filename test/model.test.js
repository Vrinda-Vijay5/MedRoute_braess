"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { evaluate, equilibria, classify, validateWardrop, detectBraess } = require("../src/model");
test("classic Braess equilibrium is verified by Wardrop conditions", () => {
  const b = evaluate(false), s = evaluate(true);
  assert.deepEqual(b.flows, { upper: 2000, lower: 2000, zigzag: 0 });
  assert.equal(b.averageCost, 65);
  assert.equal(s.averageCost, 80);
  assert.equal(s.flows.zigzag, 4000);
  assert.equal(s.latencies.upper, 85, "unilateral deviation pays incumbent variable-link load");
  assert.equal(classify(b.averageCost, s.averageCost), "harmful");
  assert.ok(s.latencies.zigzag <= s.latencies.upper);
});
test("classification handles harmful, beneficial, neutral and missing measurements", () => {
  assert.equal(classify(1, 2), "harmful");
  assert.equal(classify(2, 1), "beneficial");
  assert.equal(classify(1, 1), "neutral");
  assert.equal(classify(1, NaN), "inconclusive");
});
test("invalid demand is rejected", () => assert.throws(() => equilibria(true, 0)));
test("shortcut equilibrium verifies the interior-demand region", () => {
  const x = evaluate(true, 6000);
  assert.deepEqual(x.flows, { upper: 1500, lower: 1500, zigzag: 3000 });
  assert.ok(Math.abs(x.latencies.upper - x.latencies.zigzag) < 1e-12);
  assert.equal(x.latencies.upper, 90);
});
test("reusable Wardrop and paradox APIs validate both configurations", () => {
  assert.equal(validateWardrop(evaluate(false)), true);
  assert.equal(validateWardrop(evaluate(true)), true);
  const result = detectBraess();
  assert.equal(result.paradox, true);
  assert.equal(result.deltaAverageCost, 15);
  assert.equal(result.verdict, "harmful");
});
