"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { DEFAULT_TOPOLOGY, validateTopology, shortestPath } = require("../src/topology");
const { runComparison, compareBeforeAfter } = require("../src/playground_simulation");

test("simulation topology preserves hosts and disabled switches", () => {
  const topology = { ...DEFAULT_TOPOLOGY, disabledNodes: ["s2", "s3"] };
  assert.equal(validateTopology(topology).valid, true);
  assert.equal(shortestPath(topology, "s1", "s4"), null);
});

test("playground methods receive identical inputs but calculate independent policies", () => {
  const result = runComparison(DEFAULT_TOPOLOGY, { source: "h1", target: "h2", profile: "ECG", loadMbps: 10 });
  assert.deepEqual(Object.keys(result.methods), ["M1", "M2", "M3", "M4"]);
  for (const method of Object.values(result.methods)) {
    assert.equal(method.simulated, true);
    assert.ok(method.route);
    assert.ok(method.metrics);
  }
  assert.notEqual(result.methods.M3.reason, result.methods.M1.reason);
  assert.match(result.methods.M4.reason, /CBDR|Candidate/);
});

test("before/after comparison classifies a topology change without live claims", () => {
  const before = DEFAULT_TOPOLOGY;
  const after = JSON.parse(JSON.stringify(DEFAULT_TOPOLOGY));
  after.links.find(link => link.source === "s2" && link.target === "s3").enabled = true;
  const result = compareBeforeAfter(before, after, { source: "h1", target: "h2", profile: "ECG", loadMbps: 10 });
  assert.equal(result.simulated, true);
  for (const method of ["M1", "M2", "M3", "M4"]) assert.ok(["harmful", "beneficial", "neutral", "inconclusive"].includes(result.changes[method].verdict));
});
