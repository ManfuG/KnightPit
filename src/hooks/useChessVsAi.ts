import { useCallback, useEffect, useRef, useState } from "react";
import { getLegalMoves } from "../domain/chess/engine";
import { moveToUci, OfflineEngine } from "../services/offlineEngine";
import { formatFEN } from "../domain/chess/fen";
import { type Color } from "../domain/chess/types";
import { useChessGame, type ChessGameController, type GameControllerOptions } from "./useChessGame";

export type AiStatus = "idle" | "thinking" | "error";
export type ChessVsAiController = ChessGameController & {
  playerColor: Color;
  aiStatus: AiStatus;
  aiError: string | null;
  aiEvaluation: number | null;
};

export function useChessVsAi(options: GameControllerOptions = {}): ChessVsAiController {
  const game = useChessGame({ ...options, clocked: options.clocked ?? false });
  const [playerColor, setPlayerColor] = useState<Color>("white");
  const [aiStatus, setAiStatus] = useState<AiStatus>("idle");
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiEvaluation, setAiEvaluation] = useState<number | null>(null);
  const [visible, setVisible] = useState(() => !document.hidden);
  const playerColorRef = useRef<Color>("white");
  const engineRef = useRef<OfflineEngine | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const playMoveRef = useRef(game.playMove);
  const clocksRef = useRef(game.clocks);
  clocksRef.current = game.clocks;

  useEffect(() => {
    playMoveRef.current = game.playMove;
  }, [game.playMove]);

  useEffect(() => {
    const pause = () => {
      requestRef.current?.abort();
      requestRef.current = null;
      engineRef.current?.stop();
    };
    const visibilityChanged = () => {
      if (document.hidden) pause();
      setVisible(!document.hidden);
    };
    const pageHidden = () => {
      pause();
      setVisible(false);
    };
    document.addEventListener("visibilitychange", visibilityChanged);
    window.addEventListener("pagehide", pageHidden);
    const resumed = () => setVisible(!document.hidden);
    window.addEventListener("pageshow", visibilityChanged);
    document.addEventListener("pause", pageHidden);
    document.addEventListener("resume", resumed);
    return () => {
      document.removeEventListener("visibilitychange", visibilityChanged);
      window.removeEventListener("pagehide", pageHidden);
      window.removeEventListener("pageshow", visibilityChanged);
      document.removeEventListener("pause", pageHidden);
      document.removeEventListener("resume", resumed);
      pause();
    };
  }, []);

  useEffect(() => {
    const aiTurn = game.position.turn !== playerColorRef.current;
    if (!visible || game.phase !== "playing" || !aiTurn || game.viewedPly !== game.moves.length || game.result) {
      setAiStatus("idle");
      return undefined;
    }
    const controller = new AbortController();
    requestRef.current?.abort();
    requestRef.current = controller;
    const engine = engineRef.current ??= new OfflineEngine();
    setAiStatus("thinking");
    setAiError(null);
    const history = game.moves.map((record) => moveToUci(record));
    const remainingMs = clocksRef.current[game.position.turn] * 1_000;
    const moveTime = options.clocked
      ? Math.max(20, Math.min(1_200, remainingMs / 35, remainingMs - 100))
      : 1_200;
    engine.search(formatFEN(game.positions[0]), history, moveTime, controller.signal)
      .then((prediction) => {
        if (controller.signal.aborted || requestRef.current !== controller) return;
        const legalMove = getLegalMoves(game.position).find((move) => moveToUci(move) === prediction.move);
        if (!legalMove) throw new Error("Offline engine returned an illegal move. Start a new game.");
        playMoveRef.current(legalMove);
        setAiEvaluation(prediction.evaluation);
        setAiStatus("idle");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || requestRef.current !== controller) return;
        setAiError(error instanceof Error ? error.message : "Offline engine stopped. Start a new game.");
        setAiStatus("error");
      })
      .finally(() => {
        if (requestRef.current === controller) requestRef.current = null;
      });
    return () => {
      controller.abort();
      if (requestRef.current === controller) requestRef.current = null;
    };
  }, [game.phase, game.position, game.positions, game.moves, game.result, game.viewedPly, options.clocked, playerColor, visible]);

  const resetGame = useCallback((startingPosition?: Parameters<ChessGameController["resetGame"]>[0]) => {
    requestRef.current?.abort();
    requestRef.current = null;
    engineRef.current?.stop();
    playerColorRef.current = "white";
    setPlayerColor("white");
    setAiStatus("idle");
    setAiError(null);
    setAiEvaluation(null);
    game.resetGame(startingPosition);
  }, [game.resetGame]);

  const startGame = useCallback((startingPosition?: Parameters<ChessGameController["startGame"]>[0]) => {
    if (game.phase !== "setup") return;
    requestRef.current?.abort();
    requestRef.current = null;
    engineRef.current?.stop();
    const nextColor: Color = Math.random() < 0.5 ? "white" : "black";
    playerColorRef.current = nextColor;
    setPlayerColor(nextColor);
    setAiStatus("idle");
    setAiError(null);
    setAiEvaluation(null);
    game.startGame(startingPosition);
  }, [game.phase, game.startGame]);

  return { ...game, resetGame, startGame, playerColor, aiStatus, aiError, aiEvaluation };
}
