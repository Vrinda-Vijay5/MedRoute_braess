"use strict";

const MAX_NODES = 100;
const MAX_LINKS = 500;

function validateTopology(value) {
  const errors = [];
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { valid: false, errors: ["topology must be an object"], topology: null };
  }
  const nodes = value.nodes;
  const links = value.links;
  if (!Array.isArray(nodes) || nodes.length === 0 || nodes.length > MAX_NODES) {
    errors.push(`nodes must contain between 1 and ${MAX_NODES} entries`);
  }
  if (!Array.isArray(links) || links.length > MAX_LINKS) {
    errors.push(`links must contain between 0 and ${MAX_LINKS} entries`);
  }
  const ids = new Set();
  for (const node of Array.isArray(nodes) ? nodes : []) {
    if (typeof node !== "string" || !/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(node)) {
      errors.push(`invalid node id: ${String(node)}`);
    } else if (ids.has(node)) errors.push(`duplicate node id: ${node}`);
    else ids.add(node);
  }
  const edges = new Set();
  for (const link of Array.isArray(links) ? links : []) {
    if (!link || typeof link !== "object" || Array.isArray(link)) {
      errors.push("each link must be an object");
      continue;
    }
    const { source, target, capacityMbps = 100, latencyMs = 1, enabled = true } = link;
    if (!ids.has(source) || !ids.has(target) || source === target) {
      errors.push(`link endpoints must be distinct existing nodes: ${String(source)}-${String(target)}`);
      continue;
    }
    const key = [source, target].sort().join("\u0000");
    if (edges.has(key)) errors.push(`duplicate link: ${source}-${target}`);
    edges.add(key);
    if (typeof capacityMbps !== "number" || !Number.isFinite(capacityMbps) || capacityMbps <= 0) {
      errors.push(`link ${source}-${target} capacityMbps must be positive`);
    }
    if (typeof latencyMs !== "number" || !Number.isFinite(latencyMs) || latencyMs < 0) {
      errors.push(`link ${source}-${target} latencyMs must be non-negative`);
    }
    if (typeof enabled !== "boolean") errors.push(`link ${source}-${target} enabled must be boolean`);
  }
  if (errors.length) return { valid: false, errors, topology: null };
  return {
    valid: true,
    errors: [],
    topology: {
      name: typeof value.name === "string" ? value.name.slice(0, 80) : "Simulation topology",
      nodes: [...nodes],
      links: links.map(({ source, target, capacityMbps = 100, latencyMs = 1, enabled = true }) =>
        ({ source, target, capacityMbps, latencyMs, enabled }))
    }
  };
}

function shortestPath(topology, source, target) {
  const valid = validateTopology(topology);
  if (!valid.valid) throw new Error(valid.errors.join("; "));
  if (!valid.topology.nodes.includes(source) || !valid.topology.nodes.includes(target)) {
    throw new Error("source and target must exist in the topology");
  }
  if (source === target) return [source];
  const adjacency = new Map(valid.topology.nodes.map(node => [node, []]));
  for (const link of valid.topology.links) {
    if (!link.enabled) continue;
    adjacency.get(link.source).push(link.target);
    adjacency.get(link.target).push(link.source);
  }
  const queue = [source];
  const parent = new Map([[source, null]]);
  for (let index = 0; index < queue.length; index++) {
    const current = queue[index];
    for (const neighbor of adjacency.get(current)) {
      if (parent.has(neighbor)) continue;
      parent.set(neighbor, current);
      if (neighbor === target) {
        const path = [target];
        for (let step = target; step !== source;) {
          step = parent.get(step);
          path.push(step);
        }
        return path.reverse();
      }
      queue.push(neighbor);
    }
  }
  return null;
}

function connectedComponents(topology) {
  const valid = validateTopology(topology);
  if (!valid.valid) throw new Error(valid.errors.join("; "));
  const unseen = new Set(valid.topology.nodes);
  const components = [];
  while (unseen.size) {
    const first = unseen.values().next().value;
    const component = [];
    const queue = [first];
    unseen.delete(first);
    while (queue.length) {
      const node = queue.shift();
      component.push(node);
      for (const link of valid.topology.links) {
        if (!link.enabled) continue;
        const neighbor = link.source === node ? link.target : link.target === node ? link.source : null;
        if (neighbor && unseen.delete(neighbor)) queue.push(neighbor);
      }
    }
    components.push(component);
  }
  return components;
}

const DEFAULT_TOPOLOGY = Object.freeze({
  name: "Four-switch diamond (simulation benchmark)",
  nodes: ["s1", "s2", "s3", "s4"],
  links: [
    { source: "s1", target: "s2", capacityMbps: 100, latencyMs: 1 },
    { source: "s1", target: "s3", capacityMbps: 100, latencyMs: 1 },
    { source: "s2", target: "s4", capacityMbps: 100, latencyMs: 1 },
    { source: "s3", target: "s4", capacityMbps: 100, latencyMs: 1 },
    { source: "s2", target: "s3", capacityMbps: 100, latencyMs: 1, enabled: false }
  ]
});

module.exports = { validateTopology, shortestPath, connectedComponents, DEFAULT_TOPOLOGY };
