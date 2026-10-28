"use strict";

const LATENCY_WEIGHT = 0.6;
const LOSS_WEIGHT = 0.4;

function scoreCriticality({ latencySensitivity, lossSensitivity }) {
  for (const [name, value] of Object.entries({ latencySensitivity, lossSensitivity })) {
    if (!Number.isFinite(value) || value < 0 || value > 1) {
      throw new TypeError(`${name} must be a finite number from 0 to 1`);
    }
  }
  return 100 * (LATENCY_WEIGHT * latencySensitivity + LOSS_WEIGHT * lossSensitivity);
}

function rankClasses(classes) {
  return Object.entries(classes).map(([name, profile]) => ({
    name,
    score: scoreCriticality({
      latencySensitivity: profile.latency_sensitivity,
      lossSensitivity: profile.loss_sensitivity,
    }),
    queueId: profile.queue_id,
  })).sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));
}

function validateQueueOrder(classes) {
  try {
    return rankClasses(classes).every((profile, index) => profile.queueId === index + 1);
  } catch {
    return false;
  }
}

function classifyPatientTraffic({ latencySensitivity, lossSensitivity, criticalityScore } = {}) {
  const score = criticalityScore === undefined
    ? scoreCriticality({ latencySensitivity, lossSensitivity })
    : criticalityScore;
  if (!Number.isFinite(score) || score < 0 || score > 100) {
    throw new TypeError("criticalityScore must be a finite number from 0 to 100");
  }
  if (score >= 90) return { trafficClass: "ECG", score, reason: "criticality >= 90" };
  if (score >= 70) return { trafficClass: "ICU", score, reason: "criticality >= 70" };
  if (score >= 40) return { trafficClass: "WEARABLE", score, reason: "criticality >= 40" };
  return { trafficClass: "BACKGROUND", score, reason: "criticality < 40" };
}

module.exports = {
  LATENCY_WEIGHT, LOSS_WEIGHT, scoreCriticality, rankClasses,
  validateQueueOrder, classifyPatientTraffic
};
