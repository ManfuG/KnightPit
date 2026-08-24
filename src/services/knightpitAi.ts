import type { Position } from "../domain/chess/types";
import { squareName } from "../domain/chess/types";

export type AiPrediction = {
  move: string;
  evaluation: number;
  model_version: string;
  legal: boolean;
};

const AI_URL = import.meta.env.VITE_AI_URL ?? "http://127.0.0.1:8000";

export function moveToUci(move: { from: number; to: number; promotion?: string }): string {
  return `${squareName(move.from)}${squareName(move.to)}${move.promotion === "knight" ? "n" : move.promotion === "bishop" ? "b" : move.promotion === "rook" ? "r" : move.promotion === "queen" ? "q" : ""}`;
}

export function positionToFen(position: Position): string {
  const pieces = position.board.map((piece) => {
    if (!piece) return "1";
    const symbol = { pawn: "p", knight: "n", bishop: "b", rook: "r", queen: "q", king: "k" }[piece.type];
    return piece.color === "white" ? symbol.toUpperCase() : symbol;
  });
  const ranks: string[] = [];
  for (let rank = 0; rank < 8; rank += 1) {
    let text = "";
    let empty = 0;
    for (let file = 0; file < 8; file += 1) {
      const value = pieces[rank * 8 + file];
      if (value === "1") empty += 1;
      else {
        if (empty) text += empty;
        empty = 0;
        text += value;
      }
    }
    if (empty) text += empty;
    ranks.push(text);
  }
  const castling = `${position.castling.whiteKingside ? "K" : ""}${position.castling.whiteQueenside ? "Q" : ""}${position.castling.blackKingside ? "k" : ""}${position.castling.blackQueenside ? "q" : ""}` || "-";
  return `${ranks.join("/")} ${position.turn === "white" ? "w" : "b"} ${castling} ${position.enPassant === null ? "-" : squareName(position.enPassant)} ${position.halfmoveClock} ${position.fullmoveNumber}`;
}

export async function requestAiMove(fen: string, moves: string[], signal?: AbortSignal): Promise<AiPrediction> {
  const response = await fetch(`${AI_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fen, moves, time_budget_ms: 250 }),
    signal,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`AI request failed (${response.status}): ${detail || "unknown error"}`);
  }
  return response.json() as Promise<AiPrediction>;
}
