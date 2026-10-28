"use strict";

const fs = require("node:fs");
const path = require("node:path");

function closeEnough(actual, expected) {
  return Number.isFinite(actual) && Number.isFinite(expected) &&
    Math.abs(actual - expected) <= 1e-9 * Math.max(1, Math.abs(expected));
}

function sampleStats(values) {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) /
    (values.length - 1);
  return { mean, standard_deviation: Math.sqrt(variance) };
}

function validateScenarioArtifacts(directory, summaryValidation) {
  const errors = [];
  let config, results;
  try {
    config = JSON.parse(fs.readFileSync(path.join(directory, "config.json"), "utf8"));
    results = JSON.parse(fs.readFileSync(path.join(directory, "scenario_results.json"), "utf8"));
  } catch (error) {
    return { passed: false, errors: [`Stage 5 evidence is missing or invalid: ${error.message}`] };
  }

  const required = config.required_repetitions_per_scenario;
  const plan = config.required_scenarios;
  if (!Number.isInteger(required) || required < 3 || !plan || typeof plan !== "object") {
    errors.push("config.json does not define at least three repetitions and a scenario plan");
  }
  if (summaryValidation !== true || results.validation_passed !== true) {
    errors.push("the coordinator or saved results did not mark Stage 5 validation as passed");
  }
  if (!results.scenarios || typeof results.scenarios !== "object") {
    errors.push("scenario_results.json has no saved scenario measurements");
  }

  for (const [name, specification] of Object.entries(plan || {})) {
    const rows = results.scenarios?.[name];
    if (!Array.isArray(rows) || rows.length !== required) {
      errors.push(`${name} must contain exactly ${required} saved repetitions`);
      continue;
    }
    const ordered = [...rows].sort((a, b) => a.repetition - b.repetition);
    if (ordered.some((row, index) => row.repetition !== index + 1 || row.complete !== true ||
        row.qos_enabled !== specification.qos_enabled ||
        row.heavy_background !== specification.heavy_background ||
        row.flow_evidence?.verified !== true ||
        row.flow_evidence?.qos_enabled !== specification.qos_enabled ||
        row.flow_evidence?.class_traffic_usage?.complete !== true ||
        row.link_utilization?.complete !== true ||
        Object.values(row.per_class_metrics || {}).some(item => item.complete !== true))) {
      errors.push(`${name} has an incomplete, duplicate, or configuration-mismatched repetition`);
    }

    const classStats = results.statistics_from_saved_measurements?.[name]?.classes;
    for (const [trafficClass, measurements] of Object.entries(
      ordered[0]?.per_class_metrics || {})) {
      for (const field of ["latency_ms", "jitter_ms", "packet_loss_pct", "throughput_mbps"]) {
        const values = ordered.map(row => field === "throughput_mbps"
          ? row.per_class_metrics?.[trafficClass]?.throughput_mbps
          : row.per_class_metrics?.[trafficClass]?.metrics?.[field]);
        const stats = classStats?.[trafficClass]?.[field];
        if (values.length !== required || values.some(value => !Number.isFinite(value)) ||
            !stats || stats.n !== required || stats.complete !== true) {
          errors.push(`${name}/${trafficClass}/${field} is missing a complete saved statistic`);
          continue;
        }
        const expected = sampleStats(values);
        if (!closeEnough(stats.mean, expected.mean) ||
            !closeEnough(stats.standard_deviation, expected.standard_deviation)) {
          errors.push(`${name}/${trafficClass}/${field} statistics do not match saved measurements`);
        }
      }
    }
  }
  return { passed: errors.length === 0, errors };
}

module.exports = { validateScenarioArtifacts };
