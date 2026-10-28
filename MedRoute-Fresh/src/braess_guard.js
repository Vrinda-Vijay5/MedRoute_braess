"use strict";

const { detectBraess } = require("./model");

function assessTopologyChange({
  demand = 4000,
  baselineCost,
  candidateCost,
  threshold = 0.05
} = {}) {
  if (!Number.isFinite(demand) || demand <= 0 ||
      !Number.isFinite(threshold) || threshold < 0 ||
      (baselineCost !== undefined && (!Number.isFinite(baselineCost) || baselineCost <= 0)) ||
      (candidateCost !== undefined && (!Number.isFinite(candidateCost) || candidateCost < 0))) {
    return { verdict: "inconclusive", decision: "reject", reason: "invalid topology or cost input" };
  }
  const analytical = detectBraess(demand);
  if (baselineCost === undefined || candidateCost === undefined) {
    return {
      ...analytical,
      decision: analytical.paradox ? "reject" : "allow",
      reason: analytical.paradox ? "analytical equilibrium predicts a harmful shortcut" :
        "analytical equilibrium does not predict degradation"
    };
  }
  const relativeChange = (candidateCost - baselineCost) / baselineCost;
  const verdict = relativeChange > threshold ? "harmful" :
    relativeChange < -threshold ? "beneficial" : "neutral";
  return {
    ...analytical,
    baselineCost,
    candidateCost,
    relativeChange,
    verdict,
    decision: verdict === "harmful" ? "reject" : "allow",
    reason: verdict === "harmful" ? "measured candidate cost exceeds baseline threshold" :
      "candidate is not harmful under the configured threshold"
  };
}

module.exports = { assessTopologyChange };
