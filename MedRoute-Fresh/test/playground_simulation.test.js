"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { DEFAULT_TOPOLOGY, validateTopology, shortestPath } = require("../src/topology");
const { runComparison, compareBeforeAfter, pathStats, routeCost } = require("../src/playground_simulation");

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

test("simulated metrics use link properties and the documented route-cost formula", () => {
  const topology = { nodes: ["a", "b"], hosts: [{ id: "h1", attachedTo: "a" }, { id: "h2", attachedTo: "b" }], links: [{ source: "a", target: "b", capacityMbps: 20, latencyMs: 10, jitterMs: 4, packetLossPct: 5 }] };
  const route = require("../src/playground_simulation").paths(topology, "h1", "h2")[0];
  const metrics = pathStats(route, { criticality: 100, deadlineMs: 100 }, 10);
  assert.equal(metrics.hopCount, 1);
  assert.ok(Math.abs(metrics.packetLossPct - 5) < 1e-9);
  assert.equal(metrics.jitterMs, 4);
  assert.equal(metrics.routeCost, (metrics.averageLatencyMs / 20 + metrics.jitterMs / 5 + metrics.packetLossPct) / 3);
  assert.equal(routeCost(metrics), metrics.routeCost);
});

test("M4 exposes an independent protected-class guard evaluation", () => {
  const topology = { nodes: ["a", "b", "c", "d"], hosts: [{ id: "h1", attachedTo: "a" }, { id: "h2", attachedTo: "d" }], links: [
    { source: "a", target: "b", capacityMbps: 100, latencyMs: 1 }, { source: "b", target: "d", capacityMbps: 100, latencyMs: 1 },
    { source: "a", target: "c", capacityMbps: 100, latencyMs: 1, packetLossPct: 20 }, { source: "c", target: "d", capacityMbps: 100, latencyMs: 1, packetLossPct: 20 }
  ] };
  const result = runComparison(topology, { source: "h1", target: "h2", profile: "ECG", loadMbps: 10 });
  assert.ok(Array.isArray(result.methods.M4.criticalClassEvaluations));
  assert.match(result.methods.M4.reason, /CBDR|CRITICAL_CLASS/);
  assert.ok(result.routeOptions.length >= 2);
});

test("M4 rejects an aggregate-improving route that violates a protected deadline", () => {
  const topology = { nodes: ["a", "b", "c"], hosts: [{ id: "h1", attachedTo: "a" }, { id: "h2", attachedTo: "b" }], links: [
    { source: "a", target: "b", capacityMbps: 100, latencyMs: 100 },
    { source: "a", target: "c", capacityMbps: 100, latencyMs: 30 }, { source: "c", target: "b", capacityMbps: 100, latencyMs: 30 }
  ] };
  const m4 = runComparison(topology, { source: "h1", target: "h2", profile: "ECG", loadMbps: 10 }).methods.M4;
  assert.equal(m4.aggregateEvaluation.verdict, "beneficial");
  assert.equal(m4.decision, "baseline");
  assert.match(m4.reason, /CRITICAL_CLASS_DEGRADATION/);
  assert.ok(m4.criticalClassEvaluations.some(item => item.hardConstraintViolation));
});

test("unreachable topology produces unavailable methods and no route options", () => {
  const topology = { nodes: ["a", "b"], hosts: [{ id: "h1", attachedTo: "a" }, { id: "h2", attachedTo: "b" }], links: [] };
  const result = runComparison(topology, { source: "h1", target: "h2", profile: "ECG", loadMbps: 10 });
  assert.deepEqual(result.routeOptions, []);
  for (const method of Object.values(result.methods)) assert.equal(method.metrics, null);
});
