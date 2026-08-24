import { useCallback, useEffect, useRef, useState } from "react";
import { getLegalMoves } from "../domain/chess/engine";
import { moveToUci, positionToFen, requestAiMove } from "../services/knightpitAi";
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
  const playerColorRef = useRef<Color>("white");
  const requestRef = useRef<AbortController | null>(null);
  const requestedPlyRef = useRef<number | null>(null);
  const playMoveRef = useRef(game.playMove);

  useEffect(() => {
    playMoveRef.current = game.playMove;
  }, [game.playMove]);

  useEffect(() => {
    const aiTurn = game.position.turn !== playerColorRef.current;
    if (game.phase !== "playing" || !aiTurn || game.viewedPly !== game.moves.length || game.result) return undefined;
    if (requestedPlyRef.current === game.moves.length) return undefined;
    requestedPlyRef.current = game.moves.length;
    const controller = new AbortController();
    requestRef.current?.abort();
    requestRef.current = controller;
    setAiStatus("thinking");
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 4_000);
    const history = game.moves.map((record) => moveToUci(record));
    requestAiMove(positionToFen(game.positions[0]), history, controller.signal)
      .then((prediction) => {
        if (!prediction.legal) throw new Error("The AI service returned a non-legal move");
        const legalMove = getLegalMoves(game.position).find((move) => moveToUci(move) === prediction.move);
        if (!legalMove) throw new Error(`The AI move ${prediction.move} is not legal in the current position`);
        playMoveRef.current(legalMove);
        setAiEvaluation(prediction.evaluation);
        setAiStatus("idle");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted && !timedOut) return;
        const message = timedOut
          ? "AI request timed out · retry"
          : error instanceof Error
            ? error.message
            : "AI unavailable · retry";
        setAiError(message);
        setAiStatus("error");
      })
      .finally(() => {
        window.clearTimeout(timeout);
        if (requestRef.current === controller) requestRef.current = null;
      });
    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [game.phase, game.position, game.positions, game.moves, game.result, game.viewedPly, playerColor]);

  const resetGame = useCallback((startingPosition?: Parameters<ChessGameController["resetGame"]>[0]) => {
    requestRef.current?.abort();
    requestedPlyRef.current = null;
    playerColorRef.current = "white";
    setPlayerColor("white");
    setAiStatus("idle");
    setAiError(null);
    setAiEvaluation(null);
    game.resetGame(startingPosition);
  }, [game.resetGame]);

  const startGame = useCallback((startingPosition?: Parameters<ChessGameController["startGame"]>[0]) => {
    if (game.phase !== "setup") return;
    const nextColor: Color = Math.random() < 0.5 ? "white" : "black";
    playerColorRef.current = nextColor;
    setPlayerColor(nextColor);
    requestedPlyRef.current = null;
    setAiStatus("idle");
    setAiError(null);
    setAiEvaluation(null);
    game.startGame(startingPosition);
  }, [game.phase, game.startGame]);

  return { ...game, resetGame, startGame, playerColor, aiStatus, aiError, aiEvaluation };
}
