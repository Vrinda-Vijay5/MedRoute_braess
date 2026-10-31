(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MedRoutePlayground = factory();
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
"use strict";

// Browser-playground model only. These estimates are deliberately separate from
// live Mininet/Ryu telemetry and are never used by scripts/live_experiment.py.
const METHODS = ["M1", "M2", "M3", "M4"];
const PROFILES = {
  ECG: { criticality: 100, demandMbps: 2, deadlineMs: 50 },
  ICU: { criticality: 90, demandMbps: 4, deadlineMs: 75 },
  TELEMEDICINE: { criticality: 75, demandMbps: 8, deadlineMs: 100 },
  EHR: { criticality: 60, demandMbps: 1, deadlineMs: 150 },
  IMAGING: { criticality: 55, demandMbps: 12, deadlineMs: 200 },
  CCTV: { criticality: 10, demandMbps: 6, deadlineMs: 300 },
};

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function activeNodes(topology) {
  const blocked = new Set(topology.disabledNodes || []);
  return topology.nodes.filter(node => !blocked.has(node));
}
function endpointNode(topology, endpoint) {
  return (topology.hosts || []).find(host => host.id === endpoint)?.attachedTo || endpoint;
}
function paths(topology, source, target, limit = 64) {
  const from = endpointNode(topology, source), to = endpointNode(topology, target);
  const nodes = new Set(activeNodes(topology));
  if (!nodes.has(from) || !nodes.has(to)) return [];
  const edges = topology.links.filter(link => link.enabled !== false && nodes.has(link.source) && nodes.has(link.target));
  const adjacency = new Map(activeNodes(topology).map(node => [node, []]));
  for (const link of edges) {
    adjacency.get(link.source).push({ node: link.target, link });
    adjacency.get(link.target).push({ node: link.source, link });
  }
  const found = [];
  function walk(node, route, used) {
    if (found.length >= limit) return;
    if (node === to) { found.push({ nodes: [...route], links: route.slice(1).map((next, i) => adjacency.get(route[i]).find(x => x.node === next).link) }); return; }
    for (const edge of adjacency.get(node) || []) if (!used.has(edge.node)) {
      used.add(edge.node); route.push(edge.node); walk(edge.node, route, used); route.pop(); used.delete(edge.node);
    }
  }
  walk(from, [from], new Set([from]));
  return found;
}
function deterministicJitter(seed, index) {
  const x = Math.sin(seed * 12.9898 + index * 78.233) * 43758.5453;
  return (x - Math.floor(x)) * 2 - 1;
}
function pathStats(route, profile, loadMbps) {
  const latency = route.links.reduce((sum, link) => sum + Number(link.latencyMs || 0), 0);
  const capacity = route.links.length ? Math.min(...route.links.map(link => Number(link.capacityMbps))) : 0;
  const utilization = capacity > 0 ? loadMbps / capacity : Infinity;
  const overflow = Math.max(0, utilization - 1);
  const linkDelivery = route.links.reduce((product, link) => product * (1 - Math.min(100, Math.max(0, Number(link.packetLossPct || 0))) / 100), 1);
  const loss = Math.min(100, 100 * (1 - linkDelivery * (1 - Math.min(1, overflow))));
  const linkJitter = Math.sqrt(route.links.reduce((sum, link) => sum + Math.pow(Number(link.jitterMs || 0), 2), 0));
  const jitter = route.links.length ? linkJitter + Math.abs(utilization - 0.5) * 2 : 0;
  const throughput = Math.max(0, Math.min(loadMbps, capacity) * linkDelivery);
  const samples = Array.from({ length: 20 }, (_, i) => Math.max(0, latency + jitter * deterministicJitter(route.nodes.length + profile.criticality, i)));
  const sorted = [...samples].sort((a, b) => a - b);
  const percentile = p => sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * p) - 1)];
  const average = samples.reduce((a, b) => a + b, 0) / samples.length;
  const deadlineViolations = samples.filter(value => value > profile.deadlineMs).length / samples.length * 100;
  const routeCostValue = (average / 20 + jitter / 5 + loss / 1) / 3;
  return { averageLatencyMs: average, p95LatencyMs: percentile(.95), p99LatencyMs: percentile(.99), packetLossPct: loss, jitterMs: jitter, throughputMbps: throughput, deadlineViolationPct: deadlineViolations, capacityMbps: capacity, utilizationPct: utilization * 100, hopCount: route.links.length, routeCost: routeCostValue, congestion: utilization > 1 ? "congested" : utilization >= .8 ? "elevated" : "normal", qosViolations: deadlineViolations > 0 ? 1 : 0 };
}
function chooseRoute(method, candidates, profile, loadMbps) {
  if (!candidates.length) return null;
  if (method === "M1") return [...candidates].sort((a, b) => a.nodes.length - b.nodes.length || a.links.reduce((x, l) => x + l.latencyMs, 0) - b.links.reduce((x, l) => x + l.latencyMs, 0))[0];
  if (method === "M2") {
    // QoS-aware scoring: critical profiles weight latency and loss more heavily
    // than hop count, while still applying the same topology and demand.
    return [...candidates].sort((a, b) => {
      const left = pathStats(a, profile, loadMbps);
      const right = pathStats(b, profile, loadMbps);
      const leftScore = left.averageLatencyMs * (1 + profile.criticality / 100) + left.packetLossPct * 20;
      const rightScore = right.averageLatencyMs * (1 + profile.criticality / 100) + right.packetLossPct * 20;
      return leftScore - rightScore || a.nodes.length - b.nodes.length;
    })[0];
  }
  const scored = candidates.map(route => {
    const metrics = pathStats(route, profile, loadMbps);
    const congestionScore = metrics.utilizationPct + metrics.averageLatencyMs;
    return { route, metrics, congestionScore };
  });
  return scored.sort((a, b) => method === "M3" ? a.congestionScore - b.congestionScore : (a.metrics.averageLatencyMs * (1 + profile.criticality / 100) + a.metrics.packetLossPct * 10) - (b.metrics.averageLatencyMs * (1 + profile.criticality / 100) + b.metrics.packetLossPct * 10))[0].route;
}
function routeCost(metrics, profile) {
  return (metrics.averageLatencyMs / 20 + metrics.jitterMs / 5 + metrics.packetLossPct / 1) / 3;
}
function classifyChange(before, after, threshold = .05) {
  if (!Number.isFinite(before) || !Number.isFinite(after)) return "inconclusive";
  if (after > before * (1 + threshold)) return "harmful";
  if (after < before * (1 - threshold)) return "beneficial";
  return "neutral";
}
function criticalEvaluations(baseline, candidate, loadMbps) {
  const protectedClasses = [
    { name: "EMERGENCY_ALARM", criticality: 100, demand: Math.max(1, loadMbps * .25), deadlineMs: 50 },
    { name: "CRITICAL_PHYSIOLOGICAL_TELEMETRY", criticality: 100, demand: Math.max(1, loadMbps * .5), deadlineMs: 75 }
  ];
  return protectedClasses.map(item => {
    const base = pathStats(baseline, item, item.demand);
    const next = pathStats(candidate, item, item.demand);
    const verdict = classifyChange(routeCost(base, item), routeCost(next, item));
    const hardConstraintViolation = next.deadlineViolationPct > 0 || next.packetLossPct > 0;
    return { className: item.name, baselineCost: routeCost(base, item), candidateCost: routeCost(next, item), degradationPct: base.averageLatencyMs ? ((next.averageLatencyMs - base.averageLatencyMs) / base.averageLatencyMs) * 100 : null, verdict, hardConstraintViolation };
  });
}
function runMethod(method, topology, options) {
  const profile = PROFILES[options.profile] || PROFILES.ECG;
  const candidates = paths(topology, options.source, options.target);
  const baseline = chooseRoute(method === "M4" ? "M1" : method, candidates, profile, options.loadMbps);
  if (!baseline) return { method, status: "inconclusive", reason: "No available route", route: null, metrics: null, simulated: true };
  let selected = baseline, decision = "baseline", reason = method === "M4" ? "No candidate route exceeded the CBDR threshold" : `${method} route policy selected`, aggregateEvaluation = null, criticalClassEvaluations = [];
  if (method === "M4" && candidates.length > 1) {
    const candidate = chooseRoute("M3", candidates.filter(route => route !== baseline), profile, options.loadMbps);
    if (candidate) {
      const baseMetrics = pathStats(baseline, profile, options.loadMbps);
      const candidateMetrics = pathStats(candidate, profile, options.loadMbps);
      const baseCost = routeCost(baseMetrics, profile), candidateCost = routeCost(candidateMetrics, profile);
      aggregateEvaluation = { baselineCost: baseCost, candidateCost, verdict: classifyChange(baseCost, candidateCost) };
      criticalClassEvaluations = criticalEvaluations(baseline, candidate, options.loadMbps);
      const guardTrigger = criticalClassEvaluations.find(item => item.verdict === "harmful" || item.hardConstraintViolation);
      if (candidateCost <= baseCost * 1.05 && !options.disableCriticalGuard && !guardTrigger) { selected = candidate; decision = "accept"; reason = "Candidate cost is within the configured 5% CBDR threshold and protected critical classes are safe"; }
      else if (guardTrigger) reason = `CRITICAL_CLASS_DEGRADATION: ${guardTrigger.className} rejected the candidate (${guardTrigger.degradationPct == null ? "unavailable" : guardTrigger.degradationPct.toFixed(2) + "%"} latency change)`;
      else reason = "Candidate cost exceeds the configured 5% CBDR threshold; baseline retained";
    }
  }
  const metrics = pathStats(selected, profile, options.loadMbps);
  const nonCriticalMbps = Math.max(0, metrics.throughputMbps * (1 - profile.criticality / 200));
  return { method, status: "simulated", simulated: true, route: selected.nodes, decision, reason, aggregateEvaluation, criticalClassEvaluations, availableRoutes: candidates.map(route => route.nodes), metrics: { ...metrics, nonCriticalThroughputMbps: nonCriticalMbps, fairnessIndex: metrics.throughputMbps ? Math.min(1, (1 + profile.criticality / 100) / 2) : null, routeChanges: selected === baseline ? 0 : 1, recoveryTimeMs: options.failure ? 10 + selected.nodes.length * 2 : null, controllerOverheadMs: method === "M4" ? 2 + candidates.length : method === "M3" ? 1 + candidates.length : 1 } };
}
function runComparison(topology, options = {}) {
  const conditions = { source: options.source || "h1", target: options.target || "h2", profile: options.profile || "ECG", loadMbps: Number(options.loadMbps) || 10, failure: Boolean(options.failure) };
  const methods = Object.fromEntries(METHODS.map(method => [method, runMethod(method, topology, conditions)]));
  const allRoutes = paths(topology, conditions.source, conditions.target).map(route => ({ path: route.nodes, metrics: pathStats(route, PROFILES[conditions.profile] || PROFILES.ECG, conditions.loadMbps) }));
  allRoutes.forEach(row => {
    const users = METHODS.filter(method => methods[method].route && JSON.stringify(methods[method].route) === JSON.stringify(row.path));
    row.status = users.length ? "selected" : "alternative";
    row.selectedBy = users;
    row.reason = users.length ? users.map(method => `${method}: ${methods[method].reason}`).join("; ") : "Available but not selected by the current method policies";
  });
  return { source: conditions.source, target: conditions.target, profile: conditions.profile, loadMbps: conditions.loadMbps, simulated: true, generatedAt: new Date().toISOString(), routeOptions: allRoutes, methods };
}
function compareBeforeAfter(before, after, options = {}) {
  const oldResult = runComparison(before, options), newResult = runComparison(after, options);
  const changes = {};
  for (const method of METHODS) {
    const beforeCost = oldResult.methods[method].metrics && routeCost(oldResult.methods[method].metrics, PROFILES[options.profile || "ECG"]);
    const afterCost = newResult.methods[method].metrics && routeCost(newResult.methods[method].metrics, PROFILES[options.profile || "ECG"]);
    changes[method] = { before: beforeCost, after: afterCost, verdict: classifyChange(beforeCost, afterCost) };
  }
  return { before: oldResult, after: newResult, changes, simulated: true };
}
return { METHODS, PROFILES, clone, paths, pathStats, routeCost, classifyChange, runMethod, runComparison, compareBeforeAfter };
}));
