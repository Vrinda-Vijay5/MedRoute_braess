"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const classes = require("../sdn/classes.json").classes;
const { scoreCriticality, rankClasses, validateQueueOrder, classifyPatientTraffic } = require("../src/criticality");

test("criticality uses one deterministic latency/loss sensitivity score", () => {
  assert.equal(scoreCriticality({ latencySensitivity: 1, lossSensitivity: 1 }), 100);
  assert.equal(scoreCriticality({ latencySensitivity: 0, lossSensitivity: 0 }), 0);
  assert.deepEqual(rankClasses(classes).map(x => x.name), ["ECG", "ICU", "WEARABLE", "BACKGROUND"]);
  assert.deepEqual(rankClasses(classes).map(x => x.queueId), [1, 2, 3, 4]);
  assert.equal(validateQueueOrder(classes), true);
  const conflicting = { ...classes, ECG: { ...classes.ECG, queue_id: 4 } };
  assert.equal(validateQueueOrder(conflicting), false);
});

test("criticality rejects missing and out-of-range sensitivity inputs", () => {
  assert.throws(() => scoreCriticality({ latencySensitivity: 1, lossSensitivity: undefined }), /lossSensitivity/);
  assert.throws(() => scoreCriticality({ latencySensitivity: 1.1, lossSensitivity: 0 }), /latencySensitivity/);
});
test("patient criticality maps to the enforced traffic classes", () => {
  assert.equal(classifyPatientTraffic({ criticalityScore: 95 }).trafficClass, "ECG");
  assert.equal(classifyPatientTraffic({ criticalityScore: 75 }).trafficClass, "ICU");
  assert.equal(classifyPatientTraffic({ criticalityScore: 50 }).trafficClass, "WEARABLE");
  assert.equal(classifyPatientTraffic({ criticalityScore: 10 }).trafficClass, "BACKGROUND");
  assert.throws(() => classifyPatientTraffic({ criticalityScore: 101 }), /criticalityScore/);
});
