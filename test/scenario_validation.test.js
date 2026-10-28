"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { validateScenarioArtifacts } = require("../src/scenario_validation");

function fixture() {
  const rows = [1, 2, 3].map(repetition => ({
    repetition, complete: true, qos_enabled: true, heavy_background: false,
    link_utilization: { complete: true },
    flow_evidence: { verified: true, qos_enabled: true,
      class_traffic_usage: { complete: true } },
    per_class_metrics: { ECG: { complete: true,
      metrics: { latency_ms: repetition, jitter_ms: 1, packet_loss_pct: 0 },
      throughput_mbps: 2 } },
  }));
  return {
    config: { required_repetitions_per_scenario: 3,
      required_scenarios: { baseline: { qos_enabled: true, heavy_background: false } } },
    results: { validation_passed: true, scenarios: { baseline: rows },
      statistics_from_saved_measurements: { baseline: { classes: { ECG: {
        latency_ms: { n: 3, mean: 2, standard_deviation: 1, complete: true },
        jitter_ms: { n: 3, mean: 1, standard_deviation: 0, complete: true },
        packet_loss_pct: { n: 3, mean: 0, standard_deviation: 0, complete: true },
        throughput_mbps: { n: 3, mean: 2, standard_deviation: 0, complete: true },
      } } } } },
  };
}

test("Stage 5 accepts three complete saved repetitions and matching statistics", () => {
  const { config, results } = fixture();
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "medroute-stage5-"));
  try {
    fs.writeFileSync(path.join(directory, "config.json"), JSON.stringify(config));
    fs.writeFileSync(path.join(directory, "scenario_results.json"), JSON.stringify(results));
    assert.deepEqual(validateScenarioArtifacts(directory, true), { passed: true, errors: [] });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("Stage 5 rejects missing repetitions, mismatched statistics, and an unverified coordinator", () => {
  const { config, results } = fixture();
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "medroute-stage5-"));
  try {
    fs.writeFileSync(path.join(directory, "config.json"), JSON.stringify(config));
    results.scenarios.baseline.pop();
    results.statistics_from_saved_measurements.baseline.classes.ECG.latency_ms.mean = 999;
    fs.writeFileSync(path.join(directory, "scenario_results.json"), JSON.stringify(results));
    const result = validateScenarioArtifacts(directory, false);
    assert.equal(result.passed, false);
    assert.ok(result.errors.some(error => error.includes("exactly 3 saved repetitions")));
    assert.ok(result.errors.some(error => error.includes("did not mark Stage 5 validation")));
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
