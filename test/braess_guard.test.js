"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { assessTopologyChange } = require("../src/braess_guard");

test("analytical guard rejects the canonical harmful shortcut", () => {
  const result = assessTopologyChange();
  assert.equal(result.verdict, "harmful");
  assert.equal(result.decision, "reject");
  assert.equal(result.paradox, true);
});

test("measured guard allows beneficial changes and fails safe on invalid input", () => {
  assert.equal(assessTopologyChange({ baselineCost: 100, candidateCost: 90 }).decision, "allow");
  assert.equal(assessTopologyChange({ baselineCost: 100, candidateCost: 110 }).decision, "reject");
  assert.equal(assessTopologyChange({ baselineCost: 0 }).decision, "reject");
});
