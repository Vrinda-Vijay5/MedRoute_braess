"use strict";
function assess({ baselineMs, candidateMs, samples, expectedSamples, ageSeconds, now = Date.now() / 1000, threshold = 0.05, maxAgeSeconds = 5 }) {
  if (!Number.isFinite(baselineMs) || !Number.isFinite(candidateMs) || baselineMs <= 0 || candidateMs < 0) return { verdict: "inconclusive", route: "baseline", reason: "invalid telemetry" };
  if (!Number.isInteger(samples) || !Number.isInteger(expectedSamples) || samples < expectedSamples || expectedSamples < 1) return { verdict: "inconclusive", route: "baseline", reason: "incomplete telemetry" };
  if (!Number.isFinite(ageSeconds) || ageSeconds < 0 || ageSeconds > maxAgeSeconds || now - ageSeconds < 0) return { verdict: "inconclusive", route: "baseline", reason: "stale telemetry" };
  const ratio = candidateMs / baselineMs;
  if (ratio > 1 + threshold) return { verdict: "harmful", route: "baseline", ratio };
  if (ratio < 1 - threshold) return { verdict: "beneficial", route: "shortcut", ratio };
  return { verdict: "neutral", route: "shortcut", ratio };
}
function accepts({ infrastructureOk, baseline, shortcut, prevented, expectedRoute, actualRoute }) {
  if (!infrastructureOk) return { accepted: false, status: "infrastructure_failure" };
  if (![baseline, shortcut, prevented].every(Number.isFinite)) return { accepted: false, status: "inconclusive" };
  if (shortcut > baseline * 1.05) return { accepted: actualRoute === expectedRoute && prevented <= baseline * 1.05, status: "harmful_shortcut" };
  return { accepted: actualRoute === expectedRoute, status: "not_harmful_under_test" };
}
module.exports = { assess, accepts };
