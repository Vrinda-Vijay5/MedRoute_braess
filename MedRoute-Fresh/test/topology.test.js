"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { validateTopology, shortestPath, connectedComponents, DEFAULT_TOPOLOGY } = require("../src/topology");
const { createServer } = require("../scripts/dashboard_server");

test("general topology accepts paths beyond the diamond and handles disconnected graphs", () => {
  const topology = { nodes: ["a", "b", "c", "d", "e"], links: [
    { source: "a", target: "b" }, { source: "b", target: "c" },
    { source: "a", target: "c" }, { source: "d", target: "e", enabled: false }
  ] };
  assert.equal(validateTopology(topology).valid, true);
  assert.deepEqual(shortestPath(topology, "a", "c"), ["a", "c"]);
  assert.equal(shortestPath(topology, "a", "e"), null);
  assert.deepEqual(connectedComponents(topology), [["a", "b", "c"], ["d"], ["e"]]);
});

test("topology validation rejects invalid endpoints, duplicate links, and bad capacities", () => {
  const result = validateTopology({ nodes: ["a", "b"], links: [
    { source: "a", target: "missing" }, { source: "a", target: "b", capacityMbps: 0 },
    { source: "b", target: "a" }
  ] });
  assert.equal(result.valid, false);
  assert.ok(result.errors.some(error => error.includes("endpoints")));
  assert.ok(result.errors.some(error => error.includes("capacityMbps")));
  assert.ok(result.errors.some(error => error.includes("duplicate link")));
  assert.deepEqual(shortestPath(DEFAULT_TOPOLOGY, "s1", "s4"), ["s1", "s2", "s4"]);
});

test("dashboard topology API edits simulation state and reports disconnected routes", async t => {
  const server = createServer();
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  const page = await (await fetch(base + "/")).text();
  assert.match(page, /simulation-only topology playground/);
  const playground = await (await fetch(base + "/playground")).text();
  assert.match(playground, /Topology playground/);
  assert.match(playground, /Export JSON/);
  assert.match(playground, /Import JSON/);
  assert.match(playground, /Remove node and attached links/);
  const current = await (await fetch(base + "/api/simulation/topology")).json();
  assert.equal(current.mode, "simulation");
  const update = await fetch(base + "/api/simulation/topology", { method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "separate components", nodes: ["x", "y"], links: [] }) });
  assert.equal(update.status, 200);
  const path = await (await fetch(base + "/api/simulation/path?source=x&target=y")).json();
  assert.equal(path.reachable, false);
  assert.equal(path.route, null);
  const invalid = await fetch(base + "/api/simulation/topology", { method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nodes: ["x"], links: [{ source: "x", target: "absent" }] }) });
  assert.equal(invalid.status, 400);
  assert.deepEqual((await (await fetch(base + "/api/simulation/topology")).json()).topology.nodes, ["x", "y"]);
});
