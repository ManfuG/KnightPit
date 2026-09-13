export type Color = "white" | "black";
export type PieceType = "king" | "queen" | "rook" | "bishop" | "knight" | "pawn";
export type SquareIndex = number;
export type Board = Array<Piece | null>;

export type Piece = {
  color: Color;
  type: PieceType;
};

export type CastlingRights = {
  whiteKingside: boolean;
  whiteQueenside: boolean;
  blackKingside: boolean;
  blackQueenside: boolean;
};

export type Position = {
  board: Board;
  turn: Color;
  castling: CastlingRights;
  enPassant: SquareIndex | null;
  halfmoveClock: number;
  fullmoveNumber: number;
};

export type Move = {
  from: SquareIndex;
  to: SquareIndex;
  promotion?: Exclude<PieceType, "king" | "pawn">;
  isCastle?: "kingside" | "queenside";
  isEnPassant?: boolean;
};

export type MoveRecord = {
  ply: number;
  moveNumber: number;
  color: Color;
  notation: string;
  from: SquareIndex;
  to: SquareIndex;
  captured?: Piece;
  promotion?: Exclude<PieceType, "king" | "pawn">;
  position: Position;
  /** Mover's remaining seconds after increment; absent for untimed or older games. */
  clockSeconds?: number;
};

export type GameStatus =
  | { kind: "playing" }
  | { kind: "check" }
  | { kind: "checkmate"; winner: Color }
  | { kind: "stalemate"; winner: null }
  | { kind: "draw-insufficient-material"; winner: null };

export type GameResult = {
  winner: Color | null;
  reason: "checkmate" | "timeout" | "resignation" | "draw-agreement" | "stalemate" | "insufficient-material";
  clocks: Record<Color, number>;
};

export const files = ["a", "b", "c", "d", "e", "f", "g", "h"] as const;

export function fileOf(square: SquareIndex): number {
  return square % 8;
}

export function rankOf(square: SquareIndex): number {
  return Math.floor(square / 8);
}

export function squareName(square: SquareIndex): string {
  return `${files[fileOf(square)]}${8 - rankOf(square)}`;
}

export function squareFromName(name: string): SquareIndex {
  if (!/^[a-h][1-8]$/.test(name)) {
    throw new Error(`Invalid square: ${name}`);
  }
  return (8 - Number(name[1])) * 8 + files.indexOf(name[0] as (typeof files)[number]);
}

export function isSquareIndex(value: number): value is SquareIndex {
  return Number.isInteger(value) && value >= 0 && value < 64;
}

export function oppositeColor(color: Color): Color {
  return color === "white" ? "black" : "white";
}
