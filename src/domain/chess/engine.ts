import {
  type Board,
  type CastlingRights,
  type Color,
  type GameStatus,
  type Move,
  type Piece,
  type PieceType,
  type Position,
  type SquareIndex,
  fileOf,
  oppositeColor,
  rankOf,
  squareName,
} from "./types";

const promotionTypes: Array<Exclude<PieceType, "king" | "pawn">> = ["queen", "rook", "bishop", "knight"];
const knightOffsets = [-17, -15, -10, -6, 6, 10, 15, 17];
const kingOffsets = [-9, -8, -7, -1, 1, 7, 8, 9];
export const PIECE_VALUES: Readonly<Record<PieceType, number>> = { king: 0, queen: 9, rook: 5, bishop: 3, knight: 3, pawn: 1 };

function emptyBoard(): Board {
  return Array.from({ length: 64 }, () => null);
}

function cloneRights(rights: CastlingRights): CastlingRights {
  return { ...rights };
}

export function clonePosition(position: Position): Position {
  return {
    board: position.board.map((piece) => (piece ? { ...piece } : null)),
    turn: position.turn,
    castling: cloneRights(position.castling),
    enPassant: position.enPassant,
    halfmoveClock: position.halfmoveClock,
    fullmoveNumber: position.fullmoveNumber,
  };
}


function isInside(rank: number, file: number): boolean {
  return rank >= 0 && rank < 8 && file >= 0 && file < 8;
}

function indexAt(rank: number, file: number): SquareIndex {
  return rank * 8 + file;
}

function pushPawnMove(moves: Move[], from: SquareIndex, to: SquareIndex, rank: number): void {
  if (rank === 0 || rank === 7) {
    for (const promotion of promotionTypes) moves.push({ from, to, promotion });
  } else {
    moves.push({ from, to });
  }
}

function pushSlidingMoves(position: Position, from: SquareIndex, moves: Move[], directions: Array<[number, number]>): void {
  const piece = position.board[from];
  if (!piece) return;
  const startRank = rankOf(from);
  const startFile = fileOf(from);
  for (const [rankStep, fileStep] of directions) {
    let rank = startRank + rankStep;
    let file = startFile + fileStep;
    while (isInside(rank, file)) {
      const to = indexAt(rank, file);
      const target = position.board[to];
      if (!target) {
        moves.push({ from, to });
      } else {
        if (target.color !== piece.color && target.type !== "king") moves.push({ from, to });
        break;
      }
      rank += rankStep;
      file += fileStep;
    }
  }
}

function canCastle(position: Position, color: Color, side: "kingside" | "queenside"): boolean {
  const row = color === "white" ? 7 : 0;
  const kingSquare = indexAt(row, 4);
  const rookSquare = indexAt(row, side === "kingside" ? 7 : 0);
  const right = color === "white"
    ? side === "kingside" ? position.castling.whiteKingside : position.castling.whiteQueenside
    : side === "kingside" ? position.castling.blackKingside : position.castling.blackQueenside;
  const king = position.board[kingSquare];
  const rook = position.board[rookSquare];
  if (!right || king?.color !== color || king.type !== "king" || rook?.color !== color || rook.type !== "rook") return false;
  const emptyFiles = side === "kingside" ? [5, 6] : [1, 2, 3];
  if (emptyFiles.some((file) => position.board[indexAt(row, file)])) return false;
  const enemy = oppositeColor(color);
  const transit = side === "kingside" ? indexAt(row, 5) : indexAt(row, 3);
  const landing = side === "kingside" ? indexAt(row, 6) : indexAt(row, 2);
  return !isSquareAttacked(position, kingSquare, enemy)
    && !isSquareAttacked(position, transit, enemy)
    && !isSquareAttacked(position, landing, enemy);
}

export function createInitialPosition(): Position {
  const board = emptyBoard();
  const backRank: PieceType[] = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"];
  for (let file = 0; file < 8; file += 1) {
    board[indexAt(0, file)] = { color: "black", type: backRank[file] };
    board[indexAt(1, file)] = { color: "black", type: "pawn" };
    board[indexAt(6, file)] = { color: "white", type: "pawn" };
    board[indexAt(7, file)] = { color: "white", type: backRank[file] };
  }
  return {
    board,
    turn: "white",
    castling: { whiteKingside: true, whiteQueenside: true, blackKingside: true, blackQueenside: true },
    enPassant: null,
    halfmoveClock: 0,
    fullmoveNumber: 1,
  };
}

export function getPseudoLegalMoves(position: Position, from: SquareIndex): Move[] {
  const piece = position.board[from];
  if (!piece || piece.color !== position.turn) return [];
  const moves: Move[] = [];
  const rank = rankOf(from);
  const file = fileOf(from);

  if (piece.type === "pawn") {
    const direction = piece.color === "white" ? -1 : 1;
    const oneRank = rank + direction;
    if (isInside(oneRank, file)) {
      const oneStep = indexAt(oneRank, file);
      if (!position.board[oneStep]) {
        pushPawnMove(moves, from, oneStep, oneRank);
        const homeRank = piece.color === "white" ? 6 : 1;
        const twoRank = rank + direction * 2;
        const twoStep = indexAt(twoRank, file);
        if (rank === homeRank && !position.board[twoStep]) moves.push({ from, to: twoStep });
      }
    }
    for (const captureFile of [file - 1, file + 1]) {
      if (!isInside(oneRank, captureFile)) continue;
      const to = indexAt(oneRank, captureFile);
      const target = position.board[to];
      if (target && target.color !== piece.color && target.type !== "king") pushPawnMove(moves, from, to, oneRank);
      if (position.enPassant === to && !target) moves.push({ from, to, isEnPassant: true });
    }
  }

  if (piece.type === "knight") {
    for (const offset of knightOffsets) {
      const to = from + offset;
      if (!isInside(rankOf(to), fileOf(to))) continue;
      const toRank = rankOf(to);
      const toFile = fileOf(to);
      if (!isInside(toRank, toFile) || Math.abs(toFile - file) + Math.abs(toRank - rank) !== 3) continue;
      const target = position.board[to];
      if (!target || (target.color !== piece.color && target.type !== "king")) moves.push({ from, to });
    }
  }

  if (piece.type === "bishop" || piece.type === "queen") {
    pushSlidingMoves(position, from, moves, [[-1, -1], [-1, 1], [1, -1], [1, 1]]);
  }
  if (piece.type === "rook" || piece.type === "queen") {
    pushSlidingMoves(position, from, moves, [[-1, 0], [1, 0], [0, -1], [0, 1]]);
  }
  if (piece.type === "king") {
    for (const [rankStep, fileStep] of [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]) {
      const toRank = rank + rankStep;
      const toFile = file + fileStep;
      if (!isInside(toRank, toFile)) continue;
      const to = indexAt(toRank, toFile);
      const target = position.board[to];
      if (!target || (target.color !== piece.color && target.type !== "king")) moves.push({ from, to });
    }
    if (canCastle(position, piece.color, "kingside")) moves.push({ from, to: indexAt(rank, 6), isCastle: "kingside" });
    if (canCastle(position, piece.color, "queenside")) moves.push({ from, to: indexAt(rank, 2), isCastle: "queenside" });
  }
  return moves;
}

export function isSquareAttacked(position: Position, square: SquareIndex, byColor: Color): boolean {
  const rank = rankOf(square);
  const file = fileOf(square);
  const pawnRank = rank + (byColor === "white" ? 1 : -1);
  for (const pawnFile of [file - 1, file + 1]) {
    if (isInside(pawnRank, pawnFile)) {
      const piece = position.board[indexAt(pawnRank, pawnFile)];
      if (piece?.color === byColor && piece.type === "pawn") return true;
    }
  }
  for (const offset of knightOffsets) {
    const from = square + offset;
    if (!isInside(rankOf(from), fileOf(from)) || Math.abs(fileOf(from) - file) + Math.abs(rankOf(from) - rank) !== 3) continue;
    const piece = position.board[from];
    if (piece?.color === byColor && piece.type === "knight") return true;
  }
  for (const [rankStep, fileStep, types] of [
    [-1, -1, ["bishop", "queen"]], [-1, 1, ["bishop", "queen"]], [1, -1, ["bishop", "queen"]], [1, 1, ["bishop", "queen"]],
    [-1, 0, ["rook", "queen"]], [1, 0, ["rook", "queen"]], [0, -1, ["rook", "queen"]], [0, 1, ["rook", "queen"]],
  ] as Array<[number, number, string[]]>) {
    let currentRank = rank + rankStep;
    let currentFile = file + fileStep;
    while (isInside(currentRank, currentFile)) {
      const piece = position.board[indexAt(currentRank, currentFile)];
      if (piece) {
        if (piece.color === byColor && types.includes(piece.type)) return true;
        break;
      }
      currentRank += rankStep;
      currentFile += fileStep;
    }
  }
  for (const [rankStep, fileStep] of [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]) {
    const attackerRank = rank + rankStep;
    const attackerFile = file + fileStep;
    if (!isInside(attackerRank, attackerFile)) continue;
    const piece = position.board[indexAt(attackerRank, attackerFile)];
    if (piece?.color === byColor && piece.type === "king") return true;
  }
  return false;
}

export function isInCheck(position: Position, color: Color): boolean {
  const king = position.board.findIndex((piece) => piece?.color === color && piece.type === "king");
  return king >= 0 && isSquareAttacked(position, king, oppositeColor(color));
}

export function applyMove(position: Position, move: Move): Position {
  const next = clonePosition(position);
  const piece = next.board[move.from];
  if (!piece) return next;
  const target = next.board[move.to];
  next.board[move.from] = null;
  next.board[move.to] = move.promotion ? { color: piece.color, type: move.promotion } : piece;

  if (move.isEnPassant) {
    const capturedSquare = move.to + (piece.color === "white" ? 8 : -8);
    next.board[capturedSquare] = null;
  }
  if (move.isCastle) {
    const row = piece.color === "white" ? 7 : 0;
    const rookFrom = indexAt(row, move.isCastle === "kingside" ? 7 : 0);
    const rookTo = indexAt(row, move.isCastle === "kingside" ? 5 : 3);
    next.board[rookTo] = next.board[rookFrom];
    next.board[rookFrom] = null;
  }

  if (piece.type === "king") {
    if (piece.color === "white") next.castling.whiteKingside = next.castling.whiteQueenside = false;
    else next.castling.blackKingside = next.castling.blackQueenside = false;
  }
  if (piece.type === "rook") {
    if (move.from === 56) next.castling.whiteQueenside = false;
    if (move.from === 63) next.castling.whiteKingside = false;
    if (move.from === 0) next.castling.blackQueenside = false;
    if (move.from === 7) next.castling.blackKingside = false;
  }
  if (target?.type === "rook") {
    if (move.to === 56) next.castling.whiteQueenside = false;
    if (move.to === 63) next.castling.whiteKingside = false;
    if (move.to === 0) next.castling.blackQueenside = false;
    if (move.to === 7) next.castling.blackKingside = false;
  }

  next.enPassant = null;
  if (piece.type === "pawn" && Math.abs(move.to - move.from) === 16) next.enPassant = (move.from + move.to) / 2;
  next.halfmoveClock = piece.type === "pawn" || target || move.isEnPassant ? 0 : next.halfmoveClock + 1;
  if (piece.color === "black") next.fullmoveNumber += 1;
  next.turn = oppositeColor(piece.color);
  return next;
}

export function getLegalMoves(position: Position, from?: SquareIndex): Move[] {
  const candidates = from === undefined
    ? position.board.flatMap((piece, square) => piece?.color === position.turn ? getPseudoLegalMoves(position, square) : [])
    : getPseudoLegalMoves(position, from);
  return candidates.filter((move) => !isInCheck(applyMove(position, move), position.turn));
}

function isInsufficientMaterial(position: Position): boolean {
  const nonKings = position.board.flatMap((piece, square) => piece && piece.type !== "king" ? [{ piece, square }] : []);
  if (nonKings.length === 0) return true;
  if (nonKings.length === 1 && ["bishop", "knight"].includes(nonKings[0].piece.type)) return true;
  if (nonKings.every(({ piece }) => piece.type === "bishop")) {
    const colors = new Set(nonKings.map(({ square }) => (rankOf(square) + fileOf(square)) % 2));
    return colors.size === 1;
  }
  return false;
}

export function getGameStatus(position: Position): GameStatus {
  if (isInsufficientMaterial(position)) return { kind: "draw-insufficient-material", winner: null };
  const legalMoves = getLegalMoves(position);
  if (legalMoves.length === 0) {
    if (isInCheck(position, position.turn)) return { kind: "checkmate", winner: oppositeColor(position.turn) };
    return { kind: "stalemate", winner: null };
  }
  return isInCheck(position, position.turn) ? { kind: "check" } : { kind: "playing" };
}

export function formatMove(move: Move, positionBefore: Position, positionAfter: Position): string {
  if (move.isCastle) {
    const notation = move.isCastle === "kingside" ? "O-O" : "O-O-O";
    const status = getGameStatus(positionAfter);
    return `${notation}${status.kind === "checkmate" ? "#" : status.kind === "check" ? "+" : ""}`;
  }
  const captured = Boolean(positionBefore.board[move.to]) || Boolean(move.isEnPassant);
  const promotion = move.promotion ? `=${move.promotion[0].toUpperCase()}` : "";
  const notation = `${squareName(move.from)}${captured ? "x" : "-"}${squareName(move.to)}${promotion}`;
  const status = getGameStatus(positionAfter);
  return `${notation}${status.kind === "checkmate" ? "#" : status.kind === "check" ? "+" : ""}`;
}
export function moveValue(move: Move, position: Position): number {
  return PIECE_VALUES[position.board[move.to]?.type ?? "pawn"];
}
