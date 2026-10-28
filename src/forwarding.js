"use strict";
const routes = require("../sdn/routes.json");
function actionsFor(mode, dpid) {
  if (!routes[mode]) throw new Error(`unknown forwarding mode: ${mode}`);
  return routes[mode].filter(r => r[0] === dpid).map(([,inPort,outPort,src,dst]) => ({ inPort, outPort, src, dst }));
}
function outputFor(mode, dpid, inPort, src, dst) {
  return actionsFor(mode,dpid).find(r => r.inPort === inPort && r.src === src && r.dst === dst)?.outPort ?? null;
}
module.exports = { actionsFor, outputFor, routes };
