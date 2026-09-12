import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cleanEnv = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(KNIGHTPIT_|VITE_|VIRTUAL_ENV$|PYTHONPATH$)/i.test(key)));
const checkpointPath = "KnightPitAI/checkpoints/development-seed-42.npz";
const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const digest = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");

function fixture() {
  const directory = mkdtempSync(join(tmpdir(), "knightpit fresh checkout "));
  for (const path of ["scripts", "src", "public", "index.html", "vite.config.ts", "package.json", "KnightPitAI/src", "KnightPitAI/tools", "KnightPitAI/requirements-cpu.lock"]) {
    mkdirSync(dirname(join(directory, path)), { recursive: true });
    cpSync(join(root, path), join(directory, path), { recursive: true, filter: (source) => !source.includes("__pycache__") });
  }
  // Only npm dependencies are shared; no local Python, model, replay, or .env state is copied.
  symlinkSync(join(root, "node_modules"), join(directory, "node_modules"), process.platform === "win32" ? "junction" : "dir");
  return directory;
}

function bootstrap(directory, env = {}) {
  return spawnSync(process.execPath, ["scripts/bootstrap.mjs"], { cwd: directory, env: { ...cleanEnv, ...env }, encoding: "utf8", timeout: 180_000 });
}

async function start(directory, env = {}) {
  // Exercise the public npm command, not a test-only server entry point.
  assert.ok(process.env.npm_execpath, "Run this suite with npm run test:startup");
  const child = spawn(process.execPath, [process.env.npm_execpath, "run", "dev"], {
    cwd: directory, env: { ...cleanEnv, ...env }, stdio: ["ignore", "pipe", "pipe"], detached: process.platform !== "win32",
  });
  let output = "";
  child.stdout.on("data", (data) => { output += data; });
  child.stderr.on("data", (data) => { output += data; });
  const stop = async () => {
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
    } else {
      try { process.kill(-child.pid, "SIGTERM"); } catch (error) { if (error.code !== "ESRCH") throw error; }
    }
    const deadline = Date.now() + 10_000;
    while (Date.now() < deadline) {
      try { await fetch("http://127.0.0.1:5173", { signal: AbortSignal.timeout(200) }); }
      catch { return; }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Frontend did not stop");
  };
  try {
    const deadline = Date.now() + 180_000;
    while (!output.includes("KnightPitAI ready")) {
      if (child.exitCode !== null || Date.now() > deadline) throw new Error(output || "Startup timed out");
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return { stop, output: () => output };
  } catch (error) {
    await stop();
    throw error;
  }
}

async function predict(url, moves) {
  const response = await fetch(`${url}/predict`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fen, moves, time_budget_ms: 100 }),
  });
  assert.equal(response.status, 200, await response.clone().text());
  const result = await response.json();
  assert.equal(result.legal, true);
  assert.match(result.move, /^[a-h][1-8][a-h][1-8][qrbn]?$/);
  assert.ok(Number.isFinite(result.evaluation));
  return result;
}

test("fresh checkout starts, plays, reuses artifacts offline, and honors overrides", { timeout: 360_000 }, async (t) => {
  const directory = fixture();
  t.after(() => rmSync(directory, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }));
  const checkpoint = join(directory, checkpointPath);
  assert.equal(existsSync(checkpoint), false);
  assert.equal(existsSync(join(directory, "KnightPitAI/.venv")), false);
  let server = await start(directory);
  try {
    const health = await (await fetch("http://127.0.0.1:8000/health")).json();
    assert.equal(health.model_loaded, true);
    assert.equal(health.model_version, "development-seed-42");
    assert.equal((await fetch("http://127.0.0.1:5173")).status, 200);
    const reply = await predict("http://127.0.0.1:8000", ["e2e4"]);
    // Applying the model's reply in a subsequent request independently checks its legality.
    await predict("http://127.0.0.1:8000", ["e2e4", reply.move]);
  } finally { await server.stop(); }

  const originalHash = digest(checkpoint);
  const originalTime = statSync(checkpoint).mtimeMs;
  const offline = { PIP_NO_INDEX: "1", PIP_NO_CACHE_DIR: "1" };
  server = await start(directory, offline);
  try {
    await predict("http://127.0.0.1:8000", ["d2d4"]);
    assert.equal(digest(checkpoint), originalHash);
    assert.equal(statSync(checkpoint).mtimeMs, originalTime);
  } finally { await server.stop(); }

  const custom = join(directory, "custom model.npz");
  cpSync(checkpoint, custom);
  server = await start(directory, { ...offline, KNIGHTPIT_CHECKPOINT: "custom model.npz", KNIGHTPIT_API_PORT: "8001" });
  try {
    assert.equal((await (await fetch("http://127.0.0.1:8001/health")).json()).model_version, "custom model");
    await predict("http://127.0.0.1:8001", ["e2e4"]);
  } finally { await server.stop(); }

  rmSync(checkpoint);
  const regenerated = bootstrap(directory, offline);
  assert.equal(regenerated.status, 0, regenerated.stdout + regenerated.stderr);
  assert.equal(digest(checkpoint), originalHash, "Seeded checkpoint must regenerate identically");

  const missing = bootstrap(directory, { KNIGHTPIT_CHECKPOINT: "missing.npz" });
  assert.equal(missing.status, 1);
  assert.match(missing.stderr, /KNIGHTPIT_CHECKPOINT/);
  assert.match(missing.stderr, process.platform === "win32" ? /Remove-Item Env:KNIGHTPIT_CHECKPOINT/ : /unset KNIGHTPIT_CHECKPOINT/);
  writeFileSync(custom, "invalid checkpoint");
  const invalid = bootstrap(directory, { ...offline, KNIGHTPIT_CHECKPOINT: "custom model.npz" });
  assert.equal(invalid.status, 1);
  assert.equal(readFileSync(custom, "utf8"), "invalid checkpoint");
  assert.equal(digest(checkpoint), originalHash);

  // Remote mode must work with no Python or local checkpoint, including Vite .env files.
  const remote = fixture();
  t.after(() => rmSync(remote, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }));
  writeFileSync(join(remote, ".env.local"), "VITE_AI_URL=http://127.0.0.1:8000\n");
  const skipped = bootstrap(remote, { PATH: "", KNIGHTPIT_CHECKPOINT: "missing.npz" });
  assert.equal(skipped.status, 0, skipped.stderr);
  assert.equal(existsSync(join(remote, "KnightPitAI/.venv")), false);
  assert.equal(existsSync(join(remote, checkpointPath)), false);

  // Reuse the real model service, not a health/predict mock.
  const runtime = spawnSync(process.execPath, ["--input-type=module", "-e", "import { bootstrap } from './scripts/bootstrap.mjs'; console.log(JSON.stringify(bootstrap().python));"], { cwd: directory, env: { ...cleanEnv, ...offline }, encoding: "utf8" });
  assert.equal(runtime.status, 0, runtime.stderr);
  const python = JSON.parse(runtime.stdout.trim().split("\n").at(-1));
  const api = spawn(python.command, [...python.args, "-m", "knightpit_ai.api"], { cwd: directory, env: { ...cleanEnv, PYTHONPATH: join(directory, "KnightPitAI/src"), KNIGHTPIT_CHECKPOINT: checkpoint }, stdio: "ignore" });
  try {
    server = await start(remote);
    try { await predict("http://127.0.0.1:8000", ["e2e4"]); }
    finally { await server.stop(); }
    assert.equal(existsSync(join(remote, checkpointPath)), false);
  } finally {
    const exited = new Promise((resolve) => api.once("exit", resolve));
    api.kill();
    await exited;
  }

  rmSync(join(remote, ".env.local"));
  const noPython = bootstrap(remote, { PATH: "" });
  assert.equal(noPython.status, 1);
  assert.match(noPython.stderr, /winget install|brew install|apt-get install/);
  assert.match(noPython.stderr, /npm run dev/);

  const emptyVenv = spawnSync(python.command, [...python.args, "-m", "venv", join(remote, "KnightPitAI/.venv")], { encoding: "utf8" });
  assert.equal(emptyVenv.status, 0, emptyVenv.stderr);
  const unavailableDependencies = bootstrap(remote, { ...offline, PATH: "" });
  assert.equal(unavailableDependencies.status, 1);
  assert.match(unavailableDependencies.stderr, /--require-hashes/);
  assert.match(unavailableDependencies.stderr, /--only-binary=:all:/);
  assert.ok(unavailableDependencies.stderr.includes(join(remote, "KnightPitAI/requirements-cpu.lock")));
  const repaired = bootstrap(remote, { PATH: "" });
  assert.equal(repaired.status, 0, repaired.stdout + repaired.stderr);
  assert.equal(digest(join(remote, checkpointPath)), originalHash);
});
