#!/usr/bin/env node
"use strict";

// Standard Braess example, demand 4000. S-A and B-T latency = flow/100;
// A-T and S-B latency = 45; optional A-B latency = 0.
function cost(path, flow, secondVariableFlow = flow) {
  if (path === "upper") return flow / 100 + 45;
  if (path === "lower") return flow / 100 + 45;
  if (path === "zigzag") return (flow + secondVariableFlow) / 100;
  return Infinity;
}
function equilibria(shortcut, demand = 4000) {
  if (!(demand > 0) || !Number.isFinite(demand)) throw new Error("demand must be positive");
  if (!shortcut) return [{ upper: demand / 2, lower: demand / 2, zigzag: 0 }];
  // At D=4000, all traffic uses the shortcut: latency=80. A unilateral
  // deviation to either outer route costs 4000/100+45=85, so Wardrop holds.
  // Let q be each outer-path flow. Both variable links then carry D-q. The
  // all-shortcut equilibrium holds through D=4500; the no-shortcut equilibrium
  // holds from D=9000. In between, equal costs require D-q=4500.
  if (demand <= 4500) return [{ upper: 0, lower: 0, zigzag: demand }];
  if (demand >= 9000) return [{ upper: demand / 2, lower: demand / 2, zigzag: 0 }];
  const q = demand - 4500;
  return [{ upper: q, lower: q, zigzag: 9000 - demand }];
}
function evaluate(shortcut, demand = 4000) {
  const flows = equilibria(shortcut, demand)[0];
  // Variable-edge flow includes shortcut users: S-A carries upper+zigzag and
  // B-T carries lower+zigzag. A user deviating from the all-shortcut state
  // therefore still encounters the incumbent shortcut load on the variable edge.
  const edgeSA = flows.upper + flows.zigzag;
  const edgeBT = flows.lower + flows.zigzag;
  const latencies = { upper: cost("upper", edgeSA), lower: cost("lower", edgeBT),
    zigzag: shortcut ? cost("zigzag", edgeSA, edgeBT) : null };
  const totalCost = flows.upper * latencies.upper + flows.lower * latencies.lower + (shortcut ? flows.zigzag * latencies.zigzag : 0);
  return { shortcut, demand, flows, latencies, averageCost: totalCost / demand, totalCost };
}
function pathCosts(result) {
  return Object.entries(result.flows).map(([path, flow]) => ({
    path, flow, cost: result.latencies[path]
  }));
}
function validateWardrop(result, tolerance = 1e-9) {
  if (!result || !result.flows || !result.latencies || !Number.isFinite(result.demand) ||
      result.demand <= 0 || !Number.isFinite(tolerance) || tolerance < 0) return false;
  const paths = pathCosts(result);
  const used = paths.filter(path => path.flow > tolerance);
  if (!used.length || used.some(path => !Number.isFinite(path.cost))) return false;
  const minimum = Math.min(...paths.filter(path => Number.isFinite(path.cost)).map(path => path.cost));
  return used.every(path => Math.abs(path.cost - minimum) <= tolerance) &&
    paths.every(path => path.flow >= -tolerance &&
      (Number.isFinite(path.cost) || path.flow <= tolerance));
}
function compareConfigurations(demand = 4000) {
  const baseline = evaluate(false, demand);
  const shortcut = evaluate(true, demand);
  return {
    demand, baseline, shortcut,
    deltaAverageCost: shortcut.averageCost - baseline.averageCost,
    relativeChange: (shortcut.averageCost - baseline.averageCost) / baseline.averageCost,
    wardrop: { baseline: validateWardrop(baseline), shortcut: validateWardrop(shortcut) }
  };
}
function detectBraess(demand = 4000, tolerance = 1e-9) {
  const comparison = compareConfigurations(demand);
  const harmful = comparison.wardrop.baseline && comparison.wardrop.shortcut &&
    comparison.deltaAverageCost > tolerance;
  return {
    ...comparison,
    paradox: harmful,
    verdict: harmful ? "harmful" :
      comparison.deltaAverageCost < -tolerance ? "beneficial" : "neutral"
  };
}
function classify(before, after, threshold = 1e-9) {
  if (![before, after].every(Number.isFinite)) return "inconclusive";
  const delta = after - before;
  return delta > threshold ? "harmful" : delta < -threshold ? "beneficial" : "neutral";
}
if (require.main === module) {
  const baseline = evaluate(false), shortcut = evaluate(true);
  console.log(JSON.stringify({ model: "Wardrop Braess network; demand 4000", baseline, shortcut, classification: classify(baseline.averageCost, shortcut.averageCost), criterion: "equal latency on all used paths; unused paths no cheaper" }, null, 2));
}
module.exports = {
  cost, equilibria, evaluate, pathCosts, validateWardrop,
  compareConfigurations, detectBraess, classify
};
