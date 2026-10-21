// Runs the browser service against the actual bundled WASM in Node child processes.
// No server, browser automation dependency, or downloaded engine is needed.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "knightpit-engine-"));
const children = new Set();
let maximumWorkers = 0;
let engine;
try {
  await writeFile(join(temporary, "package.json"), '{"type":"commonjs"}');
  for (const name of ["domain/chess/types", "domain/chess/engine", "domain/chess/fen", "services/offlineEngine"]) {
    const source = (await readFile(join(root, "src", `${name}.ts`), "utf8"))
      .replaceAll("import.meta.env.BASE_URL", '"/"');
    const destination = join(temporary, `${name}.js`);
    await mkdir(dirname(destination), { recursive: true });
    await writeFile(destination, ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText);
  }
  await cp(join(root, "public/engine/stockfish-19.0.1"), join(temporary, "engine"), { recursive: true });
  globalThis.window = globalThis;
  globalThis.Worker = class {
    constructor(url) {
      this.child = spawn(process.execPath, [join(temporary, "engine/stockfish-19-lite-single.js")], { stdio: ["pipe", "pipe", "pipe"] });
      children.add(this.child);
      maximumWorkers = Math.max(maximumWorkers, children.size);
      createInterface({ input: this.child.stdout }).on("line", (line) => this.onmessage?.({ data: line }));
      this.child.stderr.on("data", (chunk) => process.stderr.write(chunk));
      this.child.on("error", () => this.onerror?.());
      this.child.on("exit", (code) => {
        children.delete(this.child);
        if (!this.terminated && code !== 0) this.onerror?.();
      });
      this.child.stdin.on("error", () => {});
    }
    postMessage(command) { this.child.stdin.write(`${command}\n`); }
    terminate() {
      this.terminated = true;
      this.child.kill();
      children.delete(this.child);
    }
  };
  const require = createRequire(import.meta.url);
  const { OfflineEngine, moveToUci } = require(join(temporary, "services/offlineEngine.js"));
  const { applyMove, createInitialPosition, getGameStatus, getLegalMoves } = require(join(temporary, "domain/chess/engine.js"));
  const { formatFEN, parseFEN } = require(join(temporary, "domain/chess/fen.js"));
  engine = new OfflineEngine();
  const initial = createInitialPosition();
  const fen = formatFEN(initial);
  const signal = new AbortController().signal;
  const white = await engine.search(fen, [], 200, signal);
  const whiteMove = getLegalMoves(initial).find((move) => moveToUci(move) === white.move);
  assert.ok(whiteMove, "White move must be legal under KnightPit rules");
  const afterWhite = applyMove(initial, whiteMove);
  const black = await engine.search(fen, [white.move], 200, signal);
  assert.ok(getLegalMoves(afterWhite).some((move) => moveToUci(move) === black.move), "Black history move must be legal");
  const mate = parseFEN("7k/8/5KQ1/8/8/8/8/8 w - - 0 1");
  const mating = await engine.search(formatFEN(mate), [], 400, signal);
  const matingMove = getLegalMoves(mate).find((move) => moveToUci(move) === mating.move);
  assert.ok(matingMove, "Mating move must be legal");
  assert.equal(getGameStatus(applyMove(mate, matingMove)).kind, "checkmate");
  const cancelled = new AbortController();
  const previous = engine.search(fen, [], 1_200, cancelled.signal);
  const rejection = assert.rejects(previous, { name: "AbortError" });
  await new Promise((resolve) => setTimeout(resolve, 30));
  cancelled.abort();
  const replacement = engine.search(fen, [], 200, signal);
  await rejection;
  const fresh = await replacement;
  assert.ok(getLegalMoves(initial).some((move) => moveToUci(move) === fresh.move), "Post-abort move must belong to the new search");
  assert.equal(maximumWorkers, 1);
  console.log(JSON.stringify({ white: white.move, black: black.move, mate: mating.move, afterAbort: fresh.move, maximumWorkers }));
} finally {
  engine?.stop();
  for (const child of children) child.kill();
  await rm(temporary, { recursive: true, force: true });
}
