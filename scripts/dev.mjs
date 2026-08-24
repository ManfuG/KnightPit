import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const aiRoot = join(root, "KnightPitAI");
const aiSource = join(aiRoot, "src");
const checkpointOverride = process.env.KNIGHTPIT_CHECKPOINT;
const checkpointCandidates = [
  checkpointOverride,
  join(aiRoot, ".campaign-smoke", "champion.npz"),
  join(aiRoot, "data", "generated", "campaign-60m", "candidate-iteration-1.npz"),
  join(aiRoot, "data", "generated", "campaign-60m", "candidate-iteration-2.npz"),
  join(aiRoot, "data", "generated", "campaign-60m", "champion.npz"),
  join(aiRoot, "checkpoints", "knightpit-epoch-0001.npz"),
].filter(Boolean).map((path) => resolve(root, path));
const checkpoint = checkpointCandidates.find((path) => existsSync(path));

if (!checkpoint) {
  console.error("KnightPitAI checkpoint not found.");
  console.error("Run the campaign first or set KNIGHTPIT_CHECKPOINT to a .npz file.");
  process.exit(1);
}

function hasAiDependencies(command, args = []) {
  return spawnSync(command, [...args, "-c", "import numpy, fastapi"], { stdio: "ignore" }).status === 0;
}
function findPython() {
  const venvPython = process.platform === "win32" ? join(aiRoot, ".venv", "Scripts", "python.exe") : join(aiRoot, ".venv", "bin", "python");
  if (existsSync(venvPython) && hasAiDependencies(venvPython)) return { command: venvPython, args: [] };
  if (hasAiDependencies("python")) return { command: "python", args: [] };
  if (process.platform === "win32" && hasAiDependencies("py", ["-3"])) return { command: "py", args: ["-3"] };
  return null;
}


async function waitForHealth(url, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_000) });
      if (response.ok) return;
    } catch {
      // The API may still be loading its checkpoint.
    }
    await new Promise((resolveRetry) => setTimeout(resolveRetry, 250));
  }
  throw new Error(`AI health check timed out at ${url}`);
}

const python = findPython();
if (!python) {
  console.error("Python with NumPy and FastAPI is required. Install KnightPitAI/requirements-cpu.lock first.");
  process.exit(1);
}
const ai = spawn(
  python.command,
  [...python.args, "-m", "knightpit_ai.api"],
  {
    cwd: aiRoot,
    env: {
      ...process.env,
      PYTHONPATH: [aiSource, process.env.PYTHONPATH].filter(Boolean).join(process.platform === "win32" ? ";" : ":"),
      KNIGHTPIT_CHECKPOINT: checkpoint,
    },
    stdio: "inherit",
    windowsHide: false,
  },
);

let frontend;
let shuttingDown = false;

function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  if (frontend && !frontend.killed) frontend.kill("SIGTERM");
  if (!ai.killed) ai.kill("SIGTERM");
  setTimeout(() => process.exit(code), 250);
}

ai.once("error", (error) => {
  console.error(`Unable to start KnightPitAI: ${error.message}`);
  shutdown(1);
});
ai.once("exit", (code) => {
  if (!shuttingDown && code !== 0) {
    console.error(`KnightPitAI exited with code ${code ?? "unknown"}.`);
    shutdown(code || 1);
  }
});

try {
  await waitForHealth("http://127.0.0.1:8000/health");
  const frontendCommand = process.platform === "win32" ? "cmd.exe" : "npm";
  const frontendArgs = process.platform === "win32"
    ? ["/d", "/s", "/c", "npm run dev:frontend -- --host 127.0.0.1"]
    : ["run", "dev:frontend", "--", "--host", "127.0.0.1"];
  frontend = spawn(frontendCommand, frontendArgs, {
    cwd: root,
    env: process.env,
    stdio: "inherit",
    windowsHide: false,
  });
  frontend.once("error", (error) => {
    console.error(`Unable to start Vite: ${error.message}`);
    shutdown(1);
  });
  frontend.once("exit", (code) => {
    if (!shuttingDown) shutdown(code || 0);
  });
  console.log(`KnightPitAI ready with ${checkpoint}`);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  shutdown(1);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));
