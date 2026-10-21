import { squareName } from "../domain/chess/types";

export type EngineMove = {
  move: string;
  evaluation: number | null;
};

type Reply = {
  accept: (line: string) => boolean;
  resolve: () => void;
  reject: (error: Error) => void;
  timer: number;
};

const abortError = () => new DOMException("Engine search cancelled", "AbortError");

// One single-threaded worker per board. Cancellation destroys its message channel,
// so a late bestmove can never be consumed by the next game/search.
export class OfflineEngine {
  private worker: Worker | null = null;
  private reply: Reply | null = null;
  private ready = false;
  private generation = 0;
  private searching = false;

  stop(): void {
    this.generation += 1;
    this.shutdown(abortError());
  }

  private shutdown(error: Error): void {
    const worker = this.worker;
    this.worker = null;
    this.ready = false;
    this.searching = false;
    if (worker) {
      worker.postMessage("stop");
      worker.terminate();
    }
    if (this.reply) {
      clearTimeout(this.reply.timer);
      this.reply.reject(error);
      this.reply = null;
    }
  }

  private waitFor(accept: Reply["accept"], timeout: number): Promise<void> {
    // ES2022 / older Android WebViews do not provide Promise.withResolvers.
    return new Promise((resolve, reject) => {
      this.reply = {
        accept, resolve, reject,
        timer: window.setTimeout(() => this.shutdown(new Error("Offline engine timed out. Start a new game.")), timeout),
      };
    });
  }

  private async initialize(): Promise<void> {
    if (this.ready) return;
    const worker = new Worker(`${import.meta.env.BASE_URL}engine/stockfish-19.0.1/stockfish-19-lite-single.js`);
    this.worker = worker;
    worker.onmessage = (event: MessageEvent<unknown>) => {
      if (this.worker !== worker || typeof event.data !== "string") return;
      for (const line of event.data.split("\n")) {
        const reply = this.reply;
        if (reply?.accept(line)) {
          clearTimeout(reply.timer);
          this.reply = null;
          reply.resolve();
        }
      }
    };
    worker.onerror = () => {
      if (this.worker === worker) this.shutdown(new Error("Offline engine could not start. Start a new game."));
    };
    const uci = this.waitFor((line) => line === "uciok", 15_000);
    worker.postMessage("uci");
    await uci;
    if (this.worker !== worker) throw abortError();
    worker.postMessage("setoption name Hash value 16");
    worker.postMessage("ucinewgame");
    const ready = this.waitFor((line) => line === "readyok", 15_000);
    worker.postMessage("isready");
    await ready;
    if (this.worker !== worker) throw abortError();
    this.ready = true;
  }

  async search(fen: string, moves: string[], moveTimeMs: number, signal: AbortSignal): Promise<EngineMove> {
    if (this.searching) this.stop();
    if (signal.aborted) throw abortError();
    const generation = ++this.generation;
    this.searching = true;
    const cancel = () => {
      if (this.generation === generation) this.stop();
    };
    signal.addEventListener("abort", cancel, { once: true });
    try {
      await this.initialize();
      if (signal.aborted || generation !== this.generation) throw abortError();
      let move = "";
      let evaluation: number | null = null;
      const initialTurn = fen.split(" ")[1] === "w" ? 1 : -1;
      const turn = moves.length % 2 === 0 ? initialTurn : -initialTurn;
      const duration = Math.max(20, Math.min(1_200, Math.floor(moveTimeMs)));
      const result = this.waitFor((line) => {
        const score = /\bscore (cp|mate) (-?\d+)/.exec(line);
        if (score && !/\b(?:lowerbound|upperbound)\b/.test(line)) {
          const value = Number(score[2]);
          evaluation = turn * (score[1] === "cp" ? value / 100 : Math.sign(value) * 100);
        }
        const best = /^bestmove (\S+)/.exec(line);
        if (!best) return false;
        move = best[1];
        return true;
      }, duration + 5_000);
      this.worker!.postMessage(`position fen ${fen}${moves.length ? ` moves ${moves.join(" ")}` : ""}`);
      this.worker!.postMessage(`go movetime ${duration}`);
      await result;
      if (signal.aborted || generation !== this.generation) throw abortError();
      if (!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(move)) throw new Error("Offline engine returned no move.");
      return { move, evaluation };
    } finally {
      signal.removeEventListener("abort", cancel);
      if (generation === this.generation) this.searching = false;
    }
  }
}

export function moveToUci(move: { from: number; to: number; promotion?: string }): string {
  return `${squareName(move.from)}${squareName(move.to)}${move.promotion === "knight" ? "n" : move.promotion === "bishop" ? "b" : move.promotion === "rook" ? "r" : move.promotion === "queen" ? "q" : ""}`;
}


