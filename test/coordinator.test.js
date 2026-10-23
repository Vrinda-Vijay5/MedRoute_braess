"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { summarizeTelemetry, evaluateCandidate, acceptance } = require("../src/coordinator");
const now = 100000;
const samples = n => Array.from({ length: 5 }, (_,i) => ({ rttMs:n+i/10, timestampMs:now-100 }));
test("coordinator requires complete, fresh, valid measurements", () => {
  assert.equal(summarizeTelemetry(samples(20),5,now).complete,true);
  assert.equal(summarizeTelemetry(samples(20).slice(0,4),5,now).complete,false);
  assert.equal(summarizeTelemetry([{rttMs:-1,timestampMs:now}],1,now).complete,false);
  assert.equal(summarizeTelemetry([{rttMs:1,timestampMs:now-31000}],1,now).reason,"stale telemetry");
});
test("coordinator fails safe and selects route from paired measurement", () => {
  assert.equal(evaluateCandidate(samples(20).slice(0,2),samples(40),now).route,"baseline");
  const harmful=evaluateCandidate(samples(20),samples(40),now);
  assert.equal(harmful.verdict,"harmful"); assert.equal(harmful.route,"baseline");
  const beneficial=evaluateCandidate(samples(40),samples(20),now);
  assert.equal(beneficial.route,"shortcut");
});
test("acceptance rejects missing stages and verifies selected OpenFlow mode", () => {
  assert.equal(acceptance({infrastructureOk:true,baseline:20,shortcut:null,prevention:null,preventionMode:"baseline",actualMode:"baseline"}).accepted,false);
  assert.equal(acceptance({infrastructureOk:true,baseline:20,shortcut:30,prevention:20,preventionMode:"baseline",actualMode:"baseline"}).accepted,true);
  assert.equal(acceptance({infrastructureOk:false}).status,"infrastructure_failure");
});
