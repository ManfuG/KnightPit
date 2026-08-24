import {
  type Board,
  type CastlingRights,
  type Position,
  squareFromName,
  squareName,
} from "./types";

const pieceTypes = {
  p: "pawn",
  n: "knight",
  b: "bishop",
  r: "rook",
  q: "queen",
  k: "king",
} as const;

const pieceSymbols: Record<NonNullable<Position["board"][number]>["type"], string> = {
  pawn: "p",
  knight: "n",
  bishop: "b",
  rook: "r",
  queen: "q",
  king: "k",
};

function parseBoard(boardField: string): Board {
  const ranks = boardField.split("/");
  if (ranks.length !== 8) throw new Error("FEN board must contain exactly eight ranks");
  const board: Board = [];

  for (const rank of ranks) {
    let width = 0;
    for (const symbol of rank) {
      if (/^[1-8]$/.test(symbol)) {
        width += Number(symbol);
        board.push(...Array.from({ length: Number(symbol) }, () => null));
        continue;
      }
      const type = pieceTypes[symbol.toLowerCase() as keyof typeof pieceTypes];
      if (!type || (symbol !== symbol.toLowerCase() && symbol !== symbol.toUpperCase())) {
        throw new Error(`Invalid FEN piece: ${symbol}`);
      }
      width += 1;
      board.push({ color: symbol === symbol.toUpperCase() ? "white" : "black", type });
    }
    if (width !== 8) throw new Error("Each FEN rank must contain exactly eight squares");
  }

  return board;
}

function parseCastling(value: string): CastlingRights {
  if (value === "-") return { whiteKingside: false, whiteQueenside: false, blackKingside: false, blackQueenside: false };
  if (!/^[KQkq]+$/.test(value) || new Set(value).size !== value.length) throw new Error("Invalid FEN castling rights");
  return {
    whiteKingside: value.includes("K"),
    whiteQueenside: value.includes("Q"),
    blackKingside: value.includes("k"),
    blackQueenside: value.includes("q"),
  };
}

function parseEnPassant(value: string): number | null {
  if (value === "-") return null;
  if (!/^[a-h][36]$/.test(value)) throw new Error("Invalid FEN en-passant square");
  return squareFromName(value);
}

function parseCounter(value: string, label: string, minimum: number): number {
  if (!/^\d+$/.test(value)) throw new Error(`Invalid FEN ${label}`);
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < minimum) throw new Error(`Invalid FEN ${label}`);
  return parsed;
}

export function parseFEN(fen: string): Position {
  const fields = fen.trim().split(/\s+/);
  if (fields.length !== 6) throw new Error("FEN must contain six fields");
  const [boardField, turnField, castlingField, enPassantField, halfmoveField, fullmoveField] = fields;
  if (turnField !== "w" && turnField !== "b") throw new Error("Invalid FEN active color");
  return {
    board: parseBoard(boardField),
    turn: turnField === "w" ? "white" : "black",
    castling: parseCastling(castlingField),
    enPassant: parseEnPassant(enPassantField),
    halfmoveClock: parseCounter(halfmoveField, "halfmove clock", 0),
    fullmoveNumber: parseCounter(fullmoveField, "fullmove number", 1),
  };
}

function formatCastling(position: Position): string {
  const rights = [
    position.castling.whiteKingside ? "K" : "",
    position.castling.whiteQueenside ? "Q" : "",
    position.castling.blackKingside ? "k" : "",
    position.castling.blackQueenside ? "q" : "",
  ].join("");
  return rights || "-";
}

export function formatFEN(position: Position): string {
  const ranks: string[] = [];
  for (let rank = 0; rank < 8; rank += 1) {
    let empty = 0;
    let output = "";
    for (let file = 0; file < 8; file += 1) {
      const piece = position.board[rank * 8 + file];
      if (!piece) {
        empty += 1;
        continue;
      }
      if (empty > 0) output += empty;
      empty = 0;
      const symbol = pieceSymbols[piece.type];
      output += piece.color === "white" ? symbol.toUpperCase() : symbol;
    }
    if (empty > 0) output += empty;
    ranks.push(output);
  }
  return [
    ranks.join("/"),
    position.turn === "white" ? "w" : "b",
    formatCastling(position),
    position.enPassant === null ? "-" : squareName(position.enPassant),
    position.halfmoveClock,
    position.fullmoveNumber,
  ].join(" ");
}

export function validatePosition(position: Position): { valid: true } | { valid: false; error: string } {
  if (position.board.length !== 64) return { valid: false, error: "The board must contain 64 squares" };
  const kings = position.board.flatMap((piece, square) => piece?.type === "king" ? [{ color: piece.color, square }] : []);
  if (kings.filter(({ color }) => color === "white").length !== 1) return { valid: false, error: "Position must contain exactly one white king" };
  if (kings.filter(({ color }) => color === "black").length !== 1) return { valid: false, error: "Position must contain exactly one black king" };

  for (const [square, piece] of position.board.entries()) {
    if (piece?.type === "pawn" && (square < 8 || square >= 56)) {
      return { valid: false, error: "Pawns cannot be placed on the first or eighth rank" };
    }
  }

  const whiteKing = kings.find(({ color }) => color === "white")?.square ?? -1;
  const blackKing = kings.find(({ color }) => color === "black")?.square ?? -1;
  if (Math.abs((whiteKing % 8) - (blackKing % 8)) <= 1 && Math.abs(Math.floor(whiteKing / 8) - Math.floor(blackKing / 8)) <= 1) {
    return { valid: false, error: "Kings cannot be adjacent" };
  }
  return { valid: true };
}
