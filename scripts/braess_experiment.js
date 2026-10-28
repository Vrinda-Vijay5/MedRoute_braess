#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { detectBraess } = require("../src/model");
const { assessTopologyChange } = require("../src/braess_guard");

const root = path.resolve(__dirname, "..");
const requested = process.argv[2];
const output = requested
  ? path.resolve(root, requested)
  : path.join(root, "artifacts", `analytical-${new Date().toISOString().replace(/[-:.]/g, "")}`);
fs.mkdirSync(output, { recursive: true });

const config = {
  model: "canonical-braess",
  demand: 4000,
  edge_costs: {
    "S-A": "flow / 100", "B-T": "flow / 100",
    "A-T": 45, "S-B": 45, "A-B": 0
  },
  decision_threshold: 0.05,
  live_network_measurement: false
};
const analytical = detectBraess(config.demand);
const guard = assessTopologyChange({ demand: config.demand });
const result = {
  configuration: config,
  analytical,
  guard,
  outcome: analytical.paradox ? "shortcut_rejected_analytically" : "no_paradox_detected",
  limitation: "This run proves the Wardrop model only; it is not Mininet forwarding evidence."
};
fs.writeFileSync(path.join(output, "config.json"), JSON.stringify(config, null, 2) + "\n");
fs.writeFileSync(path.join(output, "raw-result.json"), JSON.stringify(result, null, 2) + "\n");
fs.writeFileSync(path.join(output, "report.md"),
  `# Analytical Braess experiment\n\n` +
  `- Demand: ${config.demand}\n` +
  `- Baseline equilibrium cost: ${analytical.baseline.averageCost}\n` +
  `- Shortcut equilibrium cost: ${analytical.shortcut.averageCost}\n` +
  `- Change: ${(analytical.relativeChange * 100).toFixed(2)}%\n` +
  `- Verdict: ${analytical.verdict}\n` +
  `- Wardrop checks: baseline=${analytical.wardrop.baseline}, shortcut=${analytical.wardrop.shortcut}\n\n` +
  `${result.limitation}\n`);
console.log(JSON.stringify({ evidenceDirectory: path.relative(root, output), ...result }, null, 2));
