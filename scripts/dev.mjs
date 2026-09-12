import { spawn } from "node:child_process";
import { createServer } from "vite";
import { aiEnv, bootstrap, remoteAiUrl, root } from "./bootstrap.mjs";

let ai;
let frontend;
let shuttingDown = false;

async function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  await frontend?.close();
  if (ai?.pid && ai.exitCode === null && ai.signalCode === null) {
    const exited = new Promise((resolve) => ai.once("exit", resolve));
    ai.kill("SIGTERM");
    const timer = setTimeout(() => ai.kill("SIGKILL"), 3_000);
    await exited;
    clearTimeout(timer);
  }
  process.exit(code);
}

process.on("SIGINT", () => void shutdown(0));
process.on("SIGTERM", () => void shutdown(0));

async function waitForHealth(url) {
  const deadline = Date.now() + 30_000;
  let detail = "service unreachable";
  while (Date.now() < deadline && !shuttingDown) {
    try {
      const response = await fetch(`${url}/health`, { signal: AbortSignal.timeout(1_000) });
      const health = await response.json();
      if (response.ok && health.status === "ok" && health.model_loaded === true) return;
      detail = `HTTP ${response.status}, model_loaded=${health.model_loaded}`;
    } catch (error) {
      detail = error.message;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`AI health check failed at ${url}/health: ${detail}.\n${remoteAiUrl ? "Start the configured AI service with a loaded checkpoint, or remove VITE_AI_URL from your shell/.env files for local bootstrap." : "Check the API error above and free the configured API port."}\nRetry: npm run dev\nFrontend only: npm run dev:frontend`);
}

try {
  const local = bootstrap();
  const aiUrl = (remoteAiUrl || `http://127.0.0.1:${process.env.KNIGHTPIT_API_PORT || "8000"}`).replace(/\/$/, "");
  if (local) {
    ai = spawn(local.python.command, [...local.python.args, "-m", "knightpit_ai.api"], {
      cwd: root,
      env: { ...aiEnv, KNIGHTPIT_CHECKPOINT: local.checkpoint },
      stdio: "inherit",
    });
    ai.once("error", (error) => {
      console.error(`Unable to start KnightPitAI: ${error.message}\nRun: npm run bootstrap\nThen: npm run dev`);
      void shutdown(1);
    });
    ai.once("exit", (code) => {
      if (!shuttingDown) {
        console.error(`KnightPitAI exited with code ${code ?? "unknown"}. Check the API error above.\nRetry: npm run dev`);
        void shutdown(code || 1);
      }
    });
  }
  await waitForHealth(aiUrl);
  if (!shuttingDown) {
    frontend = await createServer({
      root,
      server: { host: "127.0.0.1", port: 5173, strictPort: true },
      define: { "import.meta.env.VITE_AI_URL": JSON.stringify(aiUrl) },
    });
    await frontend.listen();
    console.log(`KnightPitAI ready at ${aiUrl}${local ? ` with ${local.checkpoint}` : ""}`);
    frontend.printUrls();
  }
} catch (error) {
  console.error(`${error.message}\nAfter correcting the error, run: npm run dev`);
  await shutdown(1);
}
