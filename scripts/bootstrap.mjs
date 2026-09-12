import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadEnv } from "vite";

export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const aiRoot = join(root, "KnightPitAI");
const venv = join(aiRoot, ".venv");
const pythonIn = (directory) => join(directory, process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const lock = join(aiRoot, "requirements-cpu.lock");
const supportedPython = "import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] <= (3, 13)))";
const pins = Object.fromEntries([...readFileSync(lock, "utf8").matchAll(/^([\w-]+)==([^\s\\]+)/gm)].map((match) => [match[1], match[2]]));
const dependencyCheck = `import importlib.metadata as m, json, sys
pins = json.loads(sys.argv[1])
assert all(m.version(name) == version for name, version in pins.items())
import numpy, fastapi, uvicorn, pydantic`;
export const aiEnv = { ...process.env, PYTHONPATH: [join(aiRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter) };
export const remoteAiUrl = loadEnv("development", root, "VITE_").VITE_AI_URL;

function commandText(command, args) {
  const quote = (value) => `'${value.replaceAll("'", process.platform === "win32" ? "''" : "'\\''")}'`;
  return `${process.platform === "win32" ? "& " : ""}${[command, ...args].map(quote).join(" ")}`;
}

function run(python, args, message) {
  const result = spawnSync(python.command, [...python.args, ...args], { cwd: root, env: aiEnv, stdio: "inherit" });
  if (result.error || result.status !== 0) {
    throw new Error(`${message}${result.error ? `: ${result.error.message}` : ""}\nRun from the repository root:\n${commandText(python.command, [...python.args, ...args])}\nThen retry: npm run dev`);
  }
}

function probe(python, code, args = []) {
  return spawnSync(python.command, [...python.args, "-c", code, ...args], { cwd: root, env: aiEnv, stdio: "ignore", timeout: 15_000 }).status === 0;
}

function preparePython() {
  const local = { command: pythonIn(venv), args: [] };
  const candidates = [
    ...(existsSync(local.command) ? [local] : []),
    ...(process.env.VIRTUAL_ENV ? [{ command: pythonIn(process.env.VIRTUAL_ENV), args: [] }] : []),
    ...(process.platform === "win32" ? ["3.13", "3.12", "3.11", "3.10"].map((version) => ({ command: "py", args: [`-${version}`] })) : []),
    ...["python3", "python"].map((command) => ({ command, args: [] })),
  ];
  let base;
  for (const python of candidates) {
    if (!probe(python, supportedPython)) continue;
    base ??= python;
    if (probe(python, dependencyCheck, [JSON.stringify(pins)])) {
      console.log(`Reusing Python environment: ${python.command} ${python.args.join(" ")}`);
      return python;
    }
  }
  if (!base) {
    const install = process.platform === "win32" ? "winget install --exact --id Python.Python.3.13" : process.platform === "darwin" ? "brew install python@3.13" : "sudo apt-get install python3 python3-venv python3-pip";
    throw new Error(`Python 3.10–3.13 with venv and pip is required by the CPU lockfile.\nInstall it (${process.platform === "linux" ? "Debian/Ubuntu" : process.platform}): ${install}\nOpen a new terminal, then run: npm run dev`);
  }
  if (!probe(local, supportedPython)) {
    console.log("Creating KnightPitAI/.venv (no activation required)...");
    run(base, ["-m", "venv", venv], "Could not create the Python environment. Ensure Python's venv/ensurepip component is installed (Debian/Ubuntu: sudo apt-get install python3-venv).");
  }
  if (!probe(local, "import pip")) run(local, ["-m", "ensurepip", "--upgrade"], "Could not provision pip.");
  console.log("Installing locked CPU dependencies (reusing pip's download cache)...");
  const installArgs = ["-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "-r", lock];
  run(local, installArgs, "Could not install locked dependencies. Check network access and the pip error above; Python 3.10–3.13 on a platform with compatible wheels is required.");
  run(local, ["-c", dependencyCheck, JSON.stringify(pins)], `The Python environment cannot load the locked runtime. Repair it with:\n${commandText(local.command, [...installArgs, "--force-reinstall"])}`);
  return local;
}

export function bootstrap() {
  if (remoteAiUrl) {
    console.log(`Using VITE_AI_URL=${remoteAiUrl}; skipping local Python and checkpoint setup.`);
    return null;
  }
  const override = process.env.KNIGHTPIT_CHECKPOINT;
  const developmentCheckpoint = join(aiRoot, "checkpoints", "development-seed-42.npz");
  const candidates = [
    join(aiRoot, ".campaign-smoke", "champion.npz"),
    join(aiRoot, "data", "generated", "campaign-60m", "candidate-iteration-1.npz"),
    join(aiRoot, "data", "generated", "campaign-60m", "candidate-iteration-2.npz"),
    join(aiRoot, "data", "generated", "campaign-60m", "champion.npz"),
    join(aiRoot, "checkpoints", "knightpit-epoch-0001.npz"),
    developmentCheckpoint,
  ];
  const checkpoint = override ? resolve(root, override) : candidates.find(existsSync) ?? developmentCheckpoint;
  const clearOverride = process.platform === "win32" ? "Remove-Item Env:KNIGHTPIT_CHECKPOINT -ErrorAction SilentlyContinue" : "unset KNIGHTPIT_CHECKPOINT";
  if (override && !existsSync(checkpoint)) {
    throw new Error(`KNIGHTPIT_CHECKPOINT does not exist: ${checkpoint}\nCorrect its path, or use the development model:\n${clearOverride}\nnpm run dev`);
  }
  const python = preparePython();
  const args = [join(aiRoot, "tools", "prepare_checkpoint.py"), checkpoint];
  if (!override && checkpoint === developmentCheckpoint) args.push("--create");
  const recovery = override ? clearOverride : commandText(process.execPath, ["-e", `require('node:fs').renameSync(${JSON.stringify(checkpoint)}, ${JSON.stringify(`${checkpoint}.invalid-${Date.now()}`)})`]);
  run(python, args, `Checkpoint preparation failed. Existing checkpoints are never overwritten. To keep the file and fall back to a development model, run:\n${recovery}\nnpm run dev`);
  return { python, checkpoint };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    bootstrap();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
