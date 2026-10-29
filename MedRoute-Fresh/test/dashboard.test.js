"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createServer, sortRunNames } = require("../scripts/dashboard_server");

test("dashboard orders run directories by embedded timestamp, not prefix", () => {
  assert.deepEqual(sortRunNames([
    "live-20261021T140648Z", "20261022T132810Z", "20261021T234301Z",
  ]), ["20261022T132810Z", "20261021T234301Z", "live-20261021T140648Z"]);
});

test("dashboard orders overlapping run artifacts by completion time", () => {
  assert.deepEqual(sortRunNames(["20261022T150138Z", "20261022T150353Z"], {
    "20261022T150138Z": "2026-10-22T15:06:03.049Z",
    "20261022T150353Z": "2026-10-22T15:03:58.521Z",
  }), ["20261022T150138Z", "20261022T150353Z"]);
});

test("dashboard serves its page and reads saved run artifacts", async t => {
  const server = createServer();
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  const page = await fetch(base + "/");
  assert.equal(page.status, 200);
  assert.match(await page.text(), /Braess route verification/);
  const runs = await (await fetch(base + "/api/runs")).json();
  assert.ok(runs.runs.length > 0);
  const run = runs.runs[0];
  const evidence = await (await fetch(base + "/api/run/" + encodeURIComponent(run))).json();
  assert.ok(evidence.summary);
  assert.ok(evidence.files.includes("summary.json"));
  assert.equal("profile_matrix" in evidence, true);
  if (evidence.files.includes("scenario_results.json")) {
    assert.equal(typeof evidence.scenario_results.validation_passed, "boolean");
    const firstScenario = Object.values(evidence.scenario_results.scenarios)[0];
    assert.equal(firstScenario.length, evidence.scenario_results.required_repetitions);
    assert.ok(firstScenario.length >= 2);
    assert.equal("raw_process_output" in firstScenario[0], false);
    if (evidence.scenario_results.braess_shortcut_repetitions.length) {
      const decision = evidence.scenario_results.braess_shortcut_repetitions[0].decision;
      assert.ok(["harmful", "neutral", "beneficial", "inconclusive"].includes(decision.verdict));
      assert.equal(typeof decision.route_selection_verified, "boolean");
      assert.equal(typeof decision.prevention_verified, "boolean");
      assert.ok("prevention_metrics" in decision);
    }
  }
  const summary = await fetch(base + `/artifact/${encodeURIComponent(run)}/summary.json`);
  assert.equal(summary.status, 200);
  assert.match(await summary.text(), /live_experiment/);
});
