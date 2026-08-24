import { useEffect, useRef } from "react";
import { appendGameHistory, type HistoryMode, type HistoryTimeControl } from "../domain/chess/history";
import type { Color } from "../domain/chess/types";
import type { ChessGameController } from "./useChessGame";

type CompletedGame = Pick<ChessGameController, "phase" | "result" | "positions" | "moves"> & { playerColor?: Color };

export function useRecordCompletedGame(game: CompletedGame, mode: HistoryMode, timeControl: HistoryTimeControl, playerColor?: Color): void {
  const recordedRef = useRef(false);

  useEffect(() => {
    if (game.phase === "setup") {
      recordedRef.current = false;
      return;
    }
    if (game.phase !== "finished" || game.result === null || recordedRef.current) return;
    recordedRef.current = true;
    const startingPosition = game.positions[0];
    if (!startingPosition) return;
    appendGameHistory({
      mode,
      timeControl,
      playerColor,
      startingPosition,
      moves: game.moves,
      result: game.result,
    });
  }, [game, mode, timeControl, playerColor]);
}
