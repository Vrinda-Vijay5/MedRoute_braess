"use strict";
const { assess, accepts } = require("./guard");

const REQUIRED_SAMPLES = 5;
const MAX_SAMPLE_AGE_SECONDS = 30;
function summarizeTelemetry(samples, expected = REQUIRED_SAMPLES, now = Date.now()) {
  if (!Array.isArray(samples) || samples.length !== expected || expected < 1) return { complete: false, reason: "incomplete telemetry" };
  if (samples.some(s => !s || !Number.isFinite(s.rttMs) || s.rttMs < 0 || !Number.isFinite(s.timestampMs))) return { complete: false, reason: "invalid telemetry" };
  if (samples.some(s => now - s.timestampMs > MAX_SAMPLE_AGE_SECONDS * 1000 || now < s.timestampMs)) return { complete: false, reason: "stale telemetry" };
  const ordered = samples.map(s => s.rttMs).sort((a,b) => a-b);
  return { complete: true, valueMs: ordered[Math.floor(ordered.length / 2)], count: ordered.length, newestTimestampMs: Math.max(...samples.map(s => s.timestampMs)) };
}
function evaluateCandidate(baselineSamples, candidateSamples, now = Date.now()) {
  const b = summarizeTelemetry(baselineSamples, REQUIRED_SAMPLES, now);
  const c = summarizeTelemetry(candidateSamples, REQUIRED_SAMPLES, now);
  if (!b.complete || !c.complete) return { verdict: "inconclusive", route: "baseline", reason: !b.complete ? `baseline ${b.reason}` : `candidate ${c.reason}` };
  return { ...assess({ baselineMs: b.valueMs, candidateMs: c.valueMs, samples: Math.min(b.count,c.count), expectedSamples: REQUIRED_SAMPLES, ageSeconds: (now - Math.min(b.newestTimestampMs,c.newestTimestampMs))/1000, maxAgeSeconds: MAX_SAMPLE_AGE_SECONDS, now: now/1000 }), baselineMs: b.valueMs, candidateMs: c.valueMs };
}
function acceptance({ infrastructureOk, baseline, shortcut, preventionMode, prevention, actualMode }) {
  const r = accepts({ infrastructureOk, baseline, shortcut, prevented: prevention, expectedRoute: preventionMode, actualRoute: actualMode });
  if (shortcut === null || prevention === null) return { accepted: false, status: "inconclusive" };
  return r;
}
module.exports = { REQUIRED_SAMPLES, MAX_SAMPLE_AGE_SECONDS, summarizeTelemetry, evaluateCandidate, acceptance };
