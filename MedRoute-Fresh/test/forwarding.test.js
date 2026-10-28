"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { outputFor, actionsFor } = require("../src/forwarding");
test("shortcut mode changes actual switch output actions and reverses symmetrically", () => {
  assert.equal(outputFor("baseline",2,1,"10.0.0.1","10.0.0.2"),2);
  assert.equal(outputFor("shortcut",2,1,"10.0.0.1","10.0.0.2"),3);
  assert.equal(outputFor("shortcut",3,3,"10.0.0.1","10.0.0.2"),2);
  assert.equal(outputFor("shortcut",3,2,"10.0.0.2","10.0.0.1"),3);
  assert.equal(outputFor("baseline",3,3,"10.0.0.1","10.0.0.2"),null);
});

test("recovery mode routes around the failed s1-s2 link", () => {
  assert.equal(outputFor("recovery", 1, 1, "10.0.0.1", "10.0.0.2"), 3);
  assert.equal(outputFor("recovery", 3, 1, "10.0.0.1", "10.0.0.2"), 3);
  assert.equal(outputFor("recovery", 2, 3, "10.0.0.1", "10.0.0.2"), 2);
  assert.equal(outputFor("recovery", 4, 1, "10.0.0.1", "10.0.0.2"), 3);
  assert.equal(outputFor("recovery", 1, 3, "10.0.0.2", "10.0.0.1"), 1);
});
test("every installed action has valid ingress/egress and unambiguous match", () => {
  for(const mode of ["baseline","shortcut"]) for(const sw of [1,2,3,4]) {
    const rows=actionsFor(mode,sw); assert.equal(new Set(rows.map(r=>`${r.inPort}:${r.src}:${r.dst}`)).size,rows.length);
    for(const r of rows) assert.ok(r.inPort>0&&r.outPort>0&&r.inPort!==r.outPort);
  }
});
