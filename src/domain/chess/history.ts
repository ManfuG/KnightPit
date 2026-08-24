import { clonePosition } from "./engine";
import type { Color, GameResult, MoveRecord, Piece, Position } from "./types";

export type HistoryMode = "play" | "training";
export type HistoryTimeControl = "1+0" | "2+1" | "3+0" | "3+2" | "5+0" | "5+3" | "10+0" | "10+5" | "15+10" | "30+0" | "30+20" | "untimed";

export type HistoryEntry = {
  id: string;
  createdAt: string;
  mode: HistoryMode;
  timeControl: HistoryTimeControl;
  playerColor?: Color;
  startingPosition: Position;
  moves: MoveRecord[];
  result: GameResult;
};

type HistoryEnvelope = {
  version: 1;
  entries: HistoryEntry[];
};

export const HISTORY_STORAGE_KEY = "knight-pit.history";
export const HISTORY_UPDATED_EVENT = "knight-pit:history-updated";
export const HISTORY_DISPLAY_LIMIT = 20;

function clonePiece(piece: Piece | undefined): Piece | undefined {
  return piece ? { ...piece } : undefined;
}

function cloneMove(move: MoveRecord): MoveRecord {
  return {
    ...move,
    captured: clonePiece(move.captured),
    position: clonePosition(move.position),
  };
}

function cloneEntry(entry: HistoryEntry): HistoryEntry {
  return {
    ...entry,
    startingPosition: clonePosition(entry.startingPosition),
    moves: entry.moves.map(cloneMove),
    result: { ...entry.result, clocks: { ...entry.result.clocks } },
  };
}

function cloneEntries(entries: HistoryEntry[]): HistoryEntry[] {
  return entries.map(cloneEntry);
}

function isPiece(value: unknown): value is Piece {
  if (!value || typeof value !== "object") return false;
  const piece = value as Piece;
  return (piece.color === "white" || piece.color === "black")
    && ["king", "queen", "rook", "bishop", "knight", "pawn"].includes(piece.type);
}

function isPosition(value: unknown): value is Position {
  if (!value || typeof value !== "object") return false;
  const position = value as Position;
  return Array.isArray(position.board)
    && position.board.length === 64
    && position.board.every((piece) => piece === null || isPiece(piece))
    && (position.turn === "white" || position.turn === "black")
    && Boolean(position.castling)
    && typeof position.castling.whiteKingside === "boolean"
    && typeof position.castling.whiteQueenside === "boolean"
    && typeof position.castling.blackKingside === "boolean"
    && typeof position.castling.blackQueenside === "boolean"
    && (position.enPassant === null || (Number.isInteger(position.enPassant) && position.enPassant >= 0 && position.enPassant < 64))
    && Number.isFinite(position.halfmoveClock)
    && Number.isFinite(position.fullmoveNumber);
}

function isMoveRecord(value: unknown): value is MoveRecord {
  if (!value || typeof value !== "object") return false;
  const move = value as MoveRecord;
  return Number.isInteger(move.ply)
    && Number.isInteger(move.moveNumber)
    && (move.color === "white" || move.color === "black")
    && typeof move.notation === "string"
    && Number.isInteger(move.from)
    && move.from >= 0
    && move.from < 64
    && Number.isInteger(move.to)
    && move.to >= 0
    && move.to < 64
    && (move.captured === undefined || isPiece(move.captured))
    && (move.promotion === undefined || ["queen", "rook", "bishop", "knight"].includes(move.promotion))
    && isPosition(move.position);
}

function isResult(value: unknown): value is GameResult {
  if (!value || typeof value !== "object") return false;
  const result = value as GameResult;
  return (result.winner === null || result.winner === "white" || result.winner === "black")
    && ["checkmate", "timeout", "resignation", "draw-agreement", "stalemate", "insufficient-material"].includes(result.reason)
    && Boolean(result.clocks)
    && Number.isFinite(result.clocks.white)
    && Number.isFinite(result.clocks.black);
}

function isHistoryEntry(value: unknown): value is HistoryEntry {
  if (!value || typeof value !== "object") return false;
  const entry = value as HistoryEntry;
  return typeof entry.id === "string"
    && typeof entry.createdAt === "string"
    && (entry.mode === "play" || entry.mode === "training")
    && ["1+0", "2+1", "3+0", "3+2", "5+0", "5+3", "10+0", "10+5", "15+10", "30+0", "30+20", "untimed"].includes(entry.timeControl)
    && (entry.playerColor === undefined || entry.playerColor === "white" || entry.playerColor === "black")
    && isPosition(entry.startingPosition)
    && Array.isArray(entry.moves)
    && entry.moves.every(isMoveRecord)
    && isResult(entry.result);
}

function isHistoryEnvelope(value: unknown): value is HistoryEnvelope {
  if (!value || typeof value !== "object") return false;
  const envelope = value as Partial<HistoryEnvelope>;
  return envelope.version === 1 && Array.isArray(envelope.entries);
}

function playableEntries(entries: unknown[]): HistoryEntry[] {
  return entries.filter(isHistoryEntry).filter((entry) => entry.mode === "play");
}

function writeHistoryEnvelope(entries: HistoryEntry[]): void {
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify({ version: 1, entries }));
}

function createId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

export function readGameHistory(): HistoryEntry[] {
  try {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      const entries = playableEntries(parsed);
      if (parsed.every(isHistoryEntry)) {
        try {
          writeHistoryEnvelope(entries);
        } catch {
          // Keep the in-memory Play records available when migration cannot write.
        }
      }
      return cloneEntries(entries);
    }
    if (!isHistoryEnvelope(parsed)) return [];
    return cloneEntries(playableEntries(parsed.entries));
  } catch {
    return [];
  }
}

export function appendGameHistory(input: Omit<HistoryEntry, "id" | "createdAt">): HistoryEntry {
  const entry: HistoryEntry = {
    id: createId(),
    createdAt: new Date().toISOString(),
    mode: input.mode,
    timeControl: input.timeControl,
    playerColor: input.playerColor,
    startingPosition: clonePosition(input.startingPosition),
    moves: input.moves.map(cloneMove),
    result: { ...input.result, clocks: { ...input.result.clocks } },
  };

  try {
    if (typeof window !== "undefined") {
      const history = readGameHistory();
      writeHistoryEnvelope([entry, ...history]);
      window.dispatchEvent(new CustomEvent(HISTORY_UPDATED_EVENT));
    }
  } catch {
    // History is optional; never interrupt an active game when storage is unavailable.
  }

  return cloneEntry(entry);
}

export function getGameHistory(id: string): HistoryEntry | null {
  return readGameHistory().find((entry) => entry.id === id) ?? null;
}
