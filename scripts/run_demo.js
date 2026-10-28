"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const classes = require("../sdn/classes.json").classes;
const { validateQueueOrder } = require("../src/criticality");
const { validateScenarioArtifacts } = require("../src/scenario_validation");
const root = path.resolve(__dirname, "..");
const startedUtc = new Date().toISOString();
const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
let out = path.join(root, "artifacts", stamp), suffix = 1;
while (fs.existsSync(out)) out = path.join(root, "artifacts", `${stamp}-${String(suffix++).padStart(2,"0")}`);
fs.mkdirSync(out, { recursive: true });
function run(args) { return spawnSync(process.execPath, args, { cwd: root, encoding: "utf8" }); }
const model = run(["src/model.js"]);
fs.writeFileSync(path.join(out, "analytical.json"), model.stdout || "");
const tests = run(["--test"]);
fs.writeFileSync(path.join(out, "unit-tests.txt"), (tests.stdout || "") + (tests.stderr || ""));
const classPolicyOk = validateQueueOrder(classes);
const pythonCommand = process.platform === "win32" ? "python" : "python3";
const pythonAvailable = spawnSync(process.platform === "win32" ? "where" : "which", [pythonCommand], { encoding: "utf8" }).status === 0;
let pythonTests = { status: null, output: `${pythonCommand} unavailable; live metric unit tests not run on this host.\n` };
if (pythonAvailable) {
  const p = spawnSync(pythonCommand, ["-m", "unittest", "discover", "-s", "test", "-p", "test_*.py"], { cwd: root, encoding: "utf8" });
  pythonTests = { status: p.status, output: (p.stdout || "") + (p.stderr || "") };
}
fs.writeFileSync(path.join(out, "python-metric-tests.txt"), pythonTests.output);
const names = [pythonCommand, "ryu-manager", "mn", "ovs-vsctl", "ovs-ofctl", "iperf3", "tc", "ping"];
const missing = names.filter(name => {
  const x = spawnSync(process.platform === "win32" ? "where" : "which", [name], { encoding: "utf8" });
  return x.status !== 0;
});
const isRoot = process.platform === "win32" ? false : process.getuid && process.getuid() === 0;
const testsOk = tests.status === 0 && (pythonTests.status === null || pythonTests.status === 0), modelOk = model.status === 0;
let liveSummary = { live_experiment: "blocked", live_prevention_verified: false, missing_tools: missing,
  reason: missing.length ? "required live tools unavailable" : (!isRoot ? "root privileges required" : null) };
let stage5Validation = { passed: false, errors: ["live scenario evidence was not produced"] };
let stage6Artifacts = { generated: false, files: [], error: "Stage 5 measurements are unavailable" };
let liveOutput = "";
if (!testsOk || !modelOk || !classPolicyOk) {
  liveSummary.reason = "mathematical verification, class policy, or unit tests failed; live run skipped";
} else if (!missing.length && isRoot) {
  const ovs = spawnSync("ovs-vsctl", ["show"], { encoding: "utf8", timeout: 5000 });
  if (ovs.status === 0) {
    const live = spawnSync("python3", [path.join(__dirname,"live_experiment.py"), "--evidence-dir", out],
      { cwd: root, encoding: "utf8", timeout: 300000, maxBuffer: 16*1024*1024,
        env: { ...process.env, MEDROUTE_LOG: path.join(out,"controller.jsonl") } });
    liveOutput = (live.stdout || "") + (live.stderr || "");
    fs.writeFileSync(path.join(out,"live-run.log"),liveOutput);
    try { liveSummary = JSON.parse(fs.readFileSync(path.join(out,"summary.json"),"utf8")); }
    catch { liveSummary = { live_experiment: live.error ? "timeout_or_startup_failure" : "infrastructure_failure", live_prevention_verified:false, error: live.error?.message || `coordinator exit ${live.status}` }; }
    stage5Validation = liveSummary.scenario_validation_passed === true
      ? validateScenarioArtifacts(out, liveSummary.scenario_validation_passed)
      : { passed: false, errors: ["coordinator did not validate the required Stage 5 scenarios"] };
    if (stage5Validation.passed) {
      const plots = spawnSync("python3", [path.join(__dirname, "generate_stage6.py"), out],
        { cwd: root, encoding: "utf8", timeout: 120000, maxBuffer: 2 * 1024 * 1024 });
      stage6Artifacts = plots.status === 0
        ? { generated: true, files: (plots.stdout || "").trim().split(/\r?\n/).filter(Boolean), error: null }
        : { generated: false, files: [], error: (plots.stderr || plots.stdout || plots.error?.message ||
            `plot generator exited ${plots.status}`).trim() };
    }
    if (live.status !== 0 && !liveSummary.error) liveSummary.coordinator_exit_code = live.status;
  } else {
    liveSummary.reason = "Open vSwitch service is not available: " + (ovs.stderr || ovs.stdout || "ovs-vsctl show failed").trim();
  }
}
const completedUtc = new Date().toISOString();
const summary = { started_utc: startedUtc, completed_utc: completedUtc, platform: process.platform,
  mathematical_verification: modelOk ? "passed" : "failed",
  automated_tests: testsOk ? "passed" : "failed", node_tests: tests.status === 0 ? "passed" : "failed",
  class_policy_validation: classPolicyOk ? "passed" : "failed",
  python_metric_tests: pythonTests.status === null ? "not_run_python3_unavailable" : pythonTests.status === 0 ? "passed" : "failed", required_root: true,
  root_available: !!isRoot, wsl_status: process.platform === "win32" ? "unavailable in this execution (access denied during inspection)" : "not applicable",
  ...liveSummary, scenario_validation_passed: stage5Validation.passed,
  scenario_validation_errors: stage5Validation.errors,
  scenario_statistics_file: stage5Validation.passed ? "scenario_results.json" : null,
  stage6_plots_generated: stage6Artifacts.generated,
  stage6_artifact_files: stage6Artifacts.files,
  stage6_generation_error: stage6Artifacts.error };
fs.writeFileSync(path.join(out, "summary.json"), JSON.stringify(summary, null, 2) + "\n");
const report = `# MedRoute run ${path.basename(out)}\n\n- Analytical model: ${summary.mathematical_verification}.\n- Unit tests: ${summary.automated_tests}.\n- Class policy: ${summary.class_policy_validation}.\n- Live experiment: ${summary.live_experiment}.\n- Shortcut classification: ${summary.shortcut_verdict || "not measured"}.\n- Live prevention verified: ${summary.live_prevention_verified ? "yes" : "no"}.\n- Reproducible scenario validation: ${summary.scenario_validation_passed ? "passed" : "failed or unavailable"}.\n- Scenario evidence: ${summary.scenario_statistics_file || "not produced"}.\n- Scenario validation errors: ${(summary.scenario_validation_errors || []).join("; ") || "none"}.\n- Stage 6 plots and report: ${summary.stage6_plots_generated ? summary.stage6_artifact_files.join(", ") : "unavailable: " + (summary.stage6_generation_error || "not generated")}.\n- Blocker: ${summary.reason || summary.error || (summary.missing_tools?.length ? summary.missing_tools.join(", ") : "none reported")}.\n\nAnalytical results and unit checks are separate from live forwarding evidence.\n`;
fs.writeFileSync(path.join(out, "report.md"), report);
console.log(`Evidence: ${path.relative(root, out)}`);
console.log(`Model: ${summary.mathematical_verification}; unit tests: ${summary.automated_tests}; live: ${summary.live_experiment}; prevention verified: ${summary.live_prevention_verified ? "yes" : "no"}`);
if (!testsOk || !modelOk || !classPolicyOk) process.exit(1);
if (!summary.scenario_validation_passed) process.exit(2);
if (!summary.stage6_plots_generated) process.exit(2);
if (summary.live_experiment === "harmful_shortcut_prevented" || summary.live_experiment === "shortcut_not_harmful_under_test") process.exit(0);
process.exit(2);
