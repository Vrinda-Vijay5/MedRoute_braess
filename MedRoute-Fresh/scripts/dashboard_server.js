"use strict";
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { DEFAULT_TOPOLOGY, validateTopology, shortestPath, connectedComponents } = require("../src/topology");
const root = path.resolve(__dirname, "..");
const artifacts = path.join(root, "artifacts");
const controllerUrl = process.env.MEDROUTE_CONTROLLER_URL || "http://127.0.0.1:8080";
const LIVE_PROFILES = {
  balanced_diamond: { primary_bw_mbps: 100, alternate_bw_mbps: 100, primary_delay: "1ms", alternate_delay: "1ms" },
  asymmetric_diamond: { primary_bw_mbps: 100, alternate_bw_mbps: 40, primary_delay: "2ms", alternate_delay: "5ms" },
  low_capacity_diamond: { primary_bw_mbps: 25, alternate_bw_mbps: 25, primary_delay: "3ms", alternate_delay: "3ms" }
};
const mime = { ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8", ".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".log": "text/plain; charset=utf-8", ".png": "image/png" };
function json(res, value) { res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" }); res.end(JSON.stringify(value)); }
function readJson(folder, name) { try { return JSON.parse(fs.readFileSync(path.join(folder, name), "utf8")); } catch { return null; } }
function latestAnalyticalRun() {
  const candidates = fs.readdirSync(artifacts, { withFileTypes: true })
    .filter(x => x.isDirectory() && fs.existsSync(path.join(artifacts, x.name, "analytical.json")))
    .map(x => {
      const folder = path.join(artifacts, x.name);
      const summary = readJson(folder, "summary.json") || {};
      return { name: x.name, time: summary.completed_utc || summary.started_utc || "" };
    });
  return sortRunNames(candidates.map(x => x.name),
    Object.fromEntries(candidates.map(x => [x.name, x.time])))[0] || null;
}
async function liveTopology() {
  // The dashboard never substitutes the simulation graph if the controller is down.
  try {
    const response = await fetch(new URL("/medroute/topology", controllerUrl), { signal: AbortSignal.timeout(1200) });
    if (!response.ok) throw new Error("controller returned HTTP " + response.status);
    const body = await response.json();
    return { connected: true, controller_url: controllerUrl, ...body };
  } catch (error) {
    return { connected: false, source: "unavailable", controller_url: controllerUrl,
      error: String(error.message || error), switches: [], links: [], hosts: [] };
  }
}
function dashboardScenarioResults(results) {
  if (!results || typeof results !== "object") return null;
  return {
    validation_passed: results.validation_passed === true,
    required_repetitions: results.required_repetitions ?? null,
    scenarios: Object.fromEntries(Object.entries(results.scenarios || {}).map(([name, rows]) =>
      [name, Array.isArray(rows) ? rows.map(row => ({ repetition: row.repetition,
        complete: row.complete === true })) : []])),
    statistics_from_saved_measurements: Object.fromEntries(
      Object.entries(results.statistics_from_saved_measurements || {}).map(([name, value]) =>
        [name, { classes: value?.classes || {} }])),
    braess_statistics: results.braess_statistics || null,
    braess_shortcut_repetitions: (results.braess_shortcut_repetitions || []).map(row => ({
      repetition: row.repetition ?? null,
      complete: row.complete === true,
      decision: {
        verdict: row.decision?.verdict || "unavailable",
        selected_route: row.decision?.selected_route || "unavailable",
        reason: row.decision?.reason || "Reason unavailable",
        prevention_verified: row.decision?.prevention_verified === true,
        route_selection_verified: row.decision?.route_selection_verified === true,
        flows_verified: row.decision?.flows_verified === true,
        controller_recorded: row.decision?.controller_recorded === true,
        metrics_used: row.decision?.metrics_used || null,
        prevention_metrics: row.decision?.prevention_metrics || null
      }
    }))
  };
}
function sortRunNames(names, runTimes = null) {
  return [...names].sort((a, b) => {
    const timeA = runTimes ? Date.parse(runTimes[a]) : NaN;
    const timeB = runTimes ? Date.parse(runTimes[b]) : NaN;
    if (Number.isFinite(timeA) && Number.isFinite(timeB) && timeA !== timeB) return timeB - timeA;
    const stampA = a.match(/\d{8}T\d{6}Z/)?.[0] || "";
    const stampB = b.match(/\d{8}T\d{6}Z/)?.[0] || "";
    return stampB.localeCompare(stampA) || b.localeCompare(a);
  });
}
function latestProfileMatrixRun() {
  const candidates = fs.readdirSync(artifacts, { withFileTypes: true })
    .filter(x => x.isDirectory() && fs.existsSync(path.join(artifacts, x.name, "profile_matrix.json")))
    .map(x => {
      const folder = path.join(artifacts, x.name);
      const summary = readJson(folder, "summary.json") || {};
      return { name: x.name, time: summary.completed_utc || summary.started_utc || "" };
    });
  return sortRunNames(candidates.map(x => x.name),
    Object.fromEntries(candidates.map(x => [x.name, x.time])))[0] || null;
}
function shellQuote(value) { return "'" + String(value).replace(/'/g, "'\\''") + "'"; }
function wslPath(value) {
  const match = String(value).match(/^([A-Za-z]):[\\/](.*)$/);
  return match ? "/mnt/" + match[1].toLowerCase() + "/" + match[2].replace(/\\/g, "/") : value;
}
function listLiveStudies() {
  if (!fs.existsSync(artifacts)) return [];
  return fs.readdirSync(artifacts, { withFileTypes: true })
    .filter(entry => entry.isDirectory() && fs.existsSync(path.join(artifacts, entry.name, "matched_study.json")))
    .map(entry => {
      const folder = path.join(artifacts, entry.name);
      return { id: entry.name, index: readJson(folder, "matched_study.json"), report: readJson(folder, "comparison_report.json") };
    });
}
function createServer() {
  let simulationTopology = JSON.parse(JSON.stringify(DEFAULT_TOPOLOGY));
  const simulationHistory = [];
  let liveStudy = { status: "idle", output_dir: null, started_at: null, finished_at: null,
    exit_code: null, error: null, request: null };
  let liveProcess = null;
  function startLiveStudy(options) {
    const runId = "matched-dashboard-" + new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
    const outputDir = path.join(artifacts, runId);
    fs.mkdirSync(outputDir, { recursive: true });
    const liveRoot = process.env.MEDROUTE_LIVE_ROOT || root;
    const python = process.env.MEDROUTE_LIVE_PYTHON || "/home/subiw/ryu-env/bin/python";
    const args = ["scripts/matched_study.py", "--output-dir", wslPath(outputDir), "--seeds", ...options.seeds.map(String),
      "--repetitions", String(options.repetitions), "--topology-profile", options.topology_profile];
    if (options.skip_ablations) args.push("--skip-ablations");
    liveStudy = { status: "running", output_dir: outputDir, started_at: new Date().toISOString(),
      finished_at: null, exit_code: null, error: null, request: options, command: [python, ...args] };
    const log = fs.createWriteStream(path.join(outputDir, "dashboard_launcher.log"));
    if (process.platform === "win32") {
      const script = ["sudo", shellQuote(python), ...args.map(shellQuote)].join(" ");
      liveProcess = spawn("wsl.exe", ["-e", "bash", "-lc", script], { cwd: liveRoot, stdio: ["ignore", log, log] });
    } else {
      liveProcess = spawn("sudo", [python, ...args], { cwd: liveRoot, stdio: ["ignore", log, log] });
    }
    liveProcess.on("error", error => { liveStudy.status = "failed"; liveStudy.error = error.message; liveStudy.finished_at = new Date().toISOString(); liveProcess = null; });
    liveProcess.on("close", code => { liveStudy.status = code === 0 ? "complete" : "failed"; liveStudy.exit_code = code;
      liveStudy.finished_at = new Date().toISOString(); liveStudy.report = readJson(outputDir, "comparison_report.json"); liveStudy.index = readJson(outputDir, "matched_study.json"); liveProcess = null; });
    return liveStudy;
  }
  return http.createServer(async (req, res) => {
    let pathname, requestUrl;
    try { requestUrl = new URL(req.url, "http://localhost"); pathname = decodeURIComponent(requestUrl.pathname); }
    catch { res.writeHead(400).end("Bad request"); return; }
    if (pathname === "/api/live/study") {
      if (req.method === "GET") return json(res, liveStudy);
      if (req.method !== "POST") { res.writeHead(405).end("Use GET or POST"); return; }
      if (liveProcess) return jsonWithStatus(res, 409, { error: "a live matched study is already running", status: liveStudy });
      try {
        let body = "";
        for await (const chunk of req) { body += chunk; if (body.length > 32 * 1024) { res.writeHead(413).end("Study request too large"); return; } }
        const parsed = JSON.parse(body);
        const seeds = Array.isArray(parsed.seeds) ? parsed.seeds : [];
        if (!Object.prototype.hasOwnProperty.call(LIVE_PROFILES, parsed.topology_profile) ||
            seeds.length < 2 || seeds.length > 8 || seeds.some(seed => !Number.isInteger(seed) || seed < 0) ||
            new Set(seeds).size !== seeds.length || !Number.isInteger(parsed.repetitions) || parsed.repetitions < 2 || parsed.repetitions > 10) {
          return jsonWithStatus(res, 400, { error: "invalid live study configuration", allowed_profiles: Object.keys(LIVE_PROFILES),
            requirements: "2-8 distinct non-negative seeds and 2-10 repetitions" });
        }
        return json(res, startLiveStudy({ topology_profile: parsed.topology_profile, seeds,
          repetitions: parsed.repetitions, skip_ablations: parsed.skip_ablations !== false,
          topology_profile_parameters: LIVE_PROFILES[parsed.topology_profile] }));
      } catch (error) { return jsonWithStatus(res, 400, { error: "invalid live study JSON", details: [error.message] }); }
    }
    if (pathname === "/api/live/studies") return json(res, { studies: listLiveStudies() });
    const liveStudyMatch = pathname.match(/^\/api\/live\/study\/([^/]+)$/);
    if (liveStudyMatch) {
      const folder = path.resolve(artifacts, liveStudyMatch[1]);
      if (path.dirname(folder) !== artifacts || !fs.existsSync(folder)) { res.writeHead(404).end("Not found"); return; }
      return json(res, { id: liveStudyMatch[1], index: readJson(folder, "matched_study.json"), report: readJson(folder, "comparison_report.json") });
    }
    if (pathname === "/api/simulation/topology") {
      if (req.method === "GET") {
        return json(res, { mode: "simulation", topology: simulationTopology,
          components: connectedComponents(simulationTopology) });
      }
      if (req.method !== "PUT") { res.writeHead(405).end("Use GET or PUT"); return; }
      try {
        let body = "";
        for await (const chunk of req) {
          body += chunk;
          if (body.length > 128 * 1024) { res.writeHead(413).end("Topology payload too large"); return; }
        }
        const parsed = JSON.parse(body);
        const result = validateTopology(parsed);
        if (!result.valid) return jsonWithStatus(res, 400, { error: "invalid topology", details: result.errors });
        simulationTopology = result.topology;
        return json(res, { mode: "simulation", topology: simulationTopology,
          components: connectedComponents(simulationTopology) });
      } catch (error) {
        return jsonWithStatus(res, 400, { error: "invalid JSON", details: [error.message] });
      }
    }
    if (pathname === "/api/simulation/history") {
      if (req.method === "GET") return json(res, { mode: "simulation", history: simulationHistory });
      if (req.method !== "POST") { res.writeHead(405).end("Use GET or POST"); return; }
      try {
        let body = "";
        for await (const chunk of req) {
          body += chunk;
          if (body.length > 512 * 1024) { res.writeHead(413).end("History payload too large"); return; }
        }
        const parsed = JSON.parse(body);
        if (!parsed || typeof parsed !== "object" || parsed.simulated !== true || !parsed.methods) {
          return jsonWithStatus(res, 400, { error: "simulation result must include simulated=true and methods" });
        }
        simulationHistory.unshift(parsed);
        if (simulationHistory.length > 50) simulationHistory.length = 50;
        return json(res, { mode: "simulation", saved: parsed, history: simulationHistory });
      } catch (error) { return jsonWithStatus(res, 400, { error: "invalid simulation result", details: [error.message] }); }
    }
    if (pathname === "/api/simulation/path") {
      if (req.method !== "GET") { res.writeHead(405).end("Read only"); return; }
      try {
        const route = shortestPath(simulationTopology, requestUrl.searchParams.get("source"),
          requestUrl.searchParams.get("target"));
        return json(res, { mode: "simulation", route, reachable: route !== null });
      } catch (error) {
        return jsonWithStatus(res, 400, { error: "invalid route request", details: [error.message] });
      }
    }
    if (pathname === "/api/live/topology") {
      if (req.method !== "GET") { res.writeHead(405).end("Read only"); return; }
      const state = await liveTopology();
      return jsonWithStatus(res, state.connected ? 200 : 503, state);
    }
    if (req.method !== "GET") { res.writeHead(405).end("Read only"); return; }
    if (pathname === "/api/runs") {
      const names = fs.readdirSync(artifacts, { withFileTypes: true }).filter(x => x.isDirectory() && fs.existsSync(path.join(artifacts, x.name, "summary.json"))).map(x => x.name);
      const runTimes = Object.fromEntries(names.map(name => {
        const summary = readJson(path.join(artifacts, name), "summary.json") || {};
        return [name, summary.completed_utc || summary.started_utc];
      }));
      return json(res, { runs: sortRunNames(names, runTimes) });
    }
    const api = pathname.match(/^\/api\/run\/([^/]+)$/);
    if (api) {
      const folder = path.resolve(artifacts, api[1]);
      if (path.dirname(folder) !== artifacts || !fs.existsSync(folder) || !fs.statSync(folder).isDirectory()) { res.writeHead(404).end("Not found"); return; }
      const files = fs.readdirSync(folder).filter(n => fs.statSync(path.join(folder, n)).isFile()).sort();
      const summary = readJson(folder, "summary.json") || {};
      const manifest = readJson(folder, "manifest.json") || {};
      const enrichedSummary = { ...summary };
      if (!enrichedSummary.started_utc && manifest.started_at_utc) enrichedSummary.started_utc = manifest.started_at_utc;
      if (!enrichedSummary.completed_utc && manifest.finished_at_utc) enrichedSummary.completed_utc = manifest.finished_at_utc;
      const matrixRun = latestProfileMatrixRun();
      const matrixFolder = matrixRun ? path.join(artifacts, matrixRun) : null;
      const analyticalRun = fs.existsSync(path.join(folder, "analytical.json")) ? api[1] : latestAnalyticalRun();
      const analyticalFolder = analyticalRun ? path.join(artifacts, analyticalRun) : null;
      return json(res, { summary: enrichedSummary, analytical: readJson(folder, "analytical.json") || (analyticalFolder ? readJson(analyticalFolder, "analytical.json") : null), analytical_run: analyticalRun, config: readJson(folder, "config.json"), measurements: readJson(folder, "measurements.json"), profile_matrix: readJson(folder, "profile_matrix.json") || (matrixFolder ? readJson(matrixFolder, "profile_matrix.json") : null), profile_matrix_run: fs.existsSync(path.join(folder, "profile_matrix.json")) ? api[1] : matrixRun, scenario_results: dashboardScenarioResults(readJson(folder, "scenario_results.json")), files });
    }
    const artifact = pathname.match(/^\/artifact\/([^/]+)\/([^/]+)$/);
    if (artifact) {
      const folder = path.resolve(artifacts, artifact[1]), target = path.resolve(folder, artifact[2]);
      if (path.dirname(folder) !== artifacts || path.dirname(target) !== folder || !fs.existsSync(target) || !fs.statSync(target).isFile()) { res.writeHead(404).end("Not found"); return; }
      res.writeHead(200, { "Content-Type": mime[path.extname(target)] || "application/octet-stream" }); fs.createReadStream(target).pipe(res); return;
    }
    const relative = pathname === "/" ? "index.html" : pathname.replace(/^\//, "");
    if (relative === "playground") {
      const playground = path.join(root, "dashboard", "playground.html");
      if (!fs.existsSync(playground)) { res.writeHead(404).end("Not found"); return; }
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      fs.createReadStream(playground).pipe(res);
      return;
    }
    if (relative === "playground-simulation.js") {
      const simulation = path.join(root, "src", "playground_simulation.js");
      res.writeHead(200, { "Content-Type": "application/javascript; charset=utf-8" });
      fs.createReadStream(simulation).pipe(res); return;
    }
    const target = path.resolve(root, "dashboard", relative);
    if (path.dirname(target) !== path.resolve(root, "dashboard") || !fs.existsSync(target) || !fs.statSync(target).isFile()) { res.writeHead(404).end("Not found"); return; }
    if (relative === "index.html") {
      const page = fs.readFileSync(target, "utf8").replace("</header>",
        '</header><p class="run-note"><a href="/playground">Open the simulation-only topology playground</a></p>');
      res.writeHead(200, { "Content-Type": mime[".html"] });
      res.end(page);
      return;
    }
    res.writeHead(200, { "Content-Type": mime[path.extname(target)] || "application/octet-stream" }); fs.createReadStream(target).pipe(res);
  });
}
function jsonWithStatus(res, status, value) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(value));
}
if (require.main === module) createServer().listen(8765, "127.0.0.1", () => console.log("MedRoute dashboard: http://127.0.0.1:8765"));
module.exports = { createServer, sortRunNames, dashboardScenarioResults, liveTopology };
