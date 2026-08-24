import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  applyMove,
  clonePosition,
  createInitialPosition,
  formatMove,
  getGameStatus,
  getLegalMoves,
  isInCheck,
} from "../domain/chess/engine";
import {
  type Color,
  type GameResult,
  type Move,
  type MoveRecord,
  type PieceType,
  type Position,
  type SquareIndex,
  oppositeColor,
} from "../domain/chess/types";

export type TimeControlLabel = "1+0" | "2+1" | "3+0" | "3+2" | "5+0" | "5+3" | "10+0" | "10+5" | "15+10" | "30+0" | "30+20";
export type TimeControl = {
  label: TimeControlLabel;
  initialSeconds: number;
  incrementSeconds: number;
};

export const TIME_CONTROLS: TimeControl[] = [
  { label: "1+0", initialSeconds: 60, incrementSeconds: 0 },
  { label: "2+1", initialSeconds: 120, incrementSeconds: 1 },
  { label: "3+0", initialSeconds: 180, incrementSeconds: 0 },
  { label: "3+2", initialSeconds: 180, incrementSeconds: 2 },
  { label: "5+0", initialSeconds: 300, incrementSeconds: 0 },
  { label: "5+3", initialSeconds: 300, incrementSeconds: 3 },
  { label: "10+0", initialSeconds: 600, incrementSeconds: 0 },
  { label: "10+5", initialSeconds: 600, incrementSeconds: 5 },
  { label: "15+10", initialSeconds: 900, incrementSeconds: 10 },
  { label: "30+0", initialSeconds: 1800, incrementSeconds: 0 },
  { label: "30+20", initialSeconds: 1800, incrementSeconds: 20 },
];

const defaultTimeControl = TIME_CONTROLS.find((control) => control.label === "10+0")!;

export type GamePhase = "setup" | "playing" | "finished";
type Clocks = Record<Color, number>;
export type GameControllerOptions = { clocked?: boolean; initialPosition?: Position };
export type PendingPromotion = {
  from: SquareIndex;
  to: SquareIndex;
  moves: Move[];
};

export type ChessGameController = {
  phase: GamePhase;
  timeControl: TimeControl;
  position: Position;
  positions: Position[];
  moves: MoveRecord[];
  selectedSquare: SquareIndex | null;
  legalTargets: SquareIndex[];
  viewedPly: number;
  pendingPromotion: PendingPromotion | null;
  clocks: Clocks;
  result: GameResult | null;
  setTimeControl: (label: TimeControlLabel) => void;
  startGame: (startingPosition?: Position) => void;
  selectSquare: (square: SquareIndex) => void;
  playMove: (move: Move) => void;
  choosePromotion: (piece: Exclude<PieceType, "king" | "pawn">) => void;
  setViewedPly: (ply: number) => void;
  stepReplay: (direction: "backward" | "forward") => void;
  returnToLive: () => void;
  resign: () => void;
  agreeDraw: () => void;
  resetGame: (startingPosition?: Position) => void;
};

const emptyClocks: Clocks = { white: 0, black: 0 };

function cloneClocks(clocks: Clocks): Clocks {
  return { white: clocks.white, black: clocks.black };
}

function reasonForStatus(status: ReturnType<typeof getGameStatus>): GameResult["reason"] | null {
  if (status.kind === "checkmate") return "checkmate";
  if (status.kind === "stalemate") return "stalemate";
  if (status.kind === "draw-insufficient-material") return "insufficient-material";
  return null;
}

export function useChessGame(options: GameControllerOptions = {}): ChessGameController {
  const clocked = options.clocked ?? true;
  const defaultPositionRef = useRef<Position | null>(null);
  if (defaultPositionRef.current === null) {
    defaultPositionRef.current = options.initialPosition ? clonePosition(options.initialPosition) : createInitialPosition();
  }
  const defaultPosition = defaultPositionRef.current;
  const [phase, setPhase] = useState<GamePhase>("setup");
  const [timeControl, setTimeControlState] = useState<TimeControl>(defaultTimeControl);
  const [position, setPosition] = useState<Position>(() => clonePosition(defaultPosition));
  const [positions, setPositions] = useState<Position[]>(() => [clonePosition(defaultPosition)]);
  const [moves, setMoves] = useState<MoveRecord[]>([]);
  const [selectedSquare, setSelectedSquare] = useState<SquareIndex | null>(null);
  const [pendingPromotion, setPendingPromotion] = useState<PendingPromotion | null>(null);
  const [viewedPly, setViewedPlyState] = useState(0);
  const [clocks, setClocks] = useState<Clocks>(emptyClocks);
  const [result, setResult] = useState<GameResult | null>(null);
  const lastTickRef = useRef<number | null>(null);
  const livePositionRef = useRef(position);

  useEffect(() => {
    livePositionRef.current = position;
  }, [position]);

  useEffect(() => {
    if (!clocked || phase !== "playing") {
      lastTickRef.current = null;
      return undefined;
    }
    lastTickRef.current = Date.now();
    const interval = window.setInterval(() => {
      const now = Date.now();
      const elapsed = (now - (lastTickRef.current ?? now)) / 1000;
      lastTickRef.current = now;
      setClocks((current) => {
        const active = livePositionRef.current.turn;
        return { ...current, [active]: Math.max(0, current[active] - elapsed) };
      });
    }, 100);
    return () => window.clearInterval(interval);
  }, [clocked, phase, position.turn]);

  useEffect(() => {
    if (!clocked || phase !== "playing" || clocks[position.turn] > 0) return;
    const winner = oppositeColor(position.turn);
    setResult({ winner, reason: "timeout", clocks: cloneClocks(clocks) });
    setPhase("finished");
    setSelectedSquare(null);
    setPendingPromotion(null);
  }, [clocked, clocks, phase, position.turn]);

  const legalTargets = useMemo(() => {
    if (phase !== "playing" || viewedPly !== moves.length || selectedSquare === null || pendingPromotion) return [];
    return getLegalMoves(position, selectedSquare).map((move) => move.to).filter((square, index, all) => all.indexOf(square) === index);
  }, [moves.length, pendingPromotion, phase, position, selectedSquare, viewedPly]);

  const setTimeControl = useCallback((label: TimeControlLabel) => {
    if (phase !== "setup") return;
    const selected = TIME_CONTROLS.find((control) => control.label === label);
    if (selected) setTimeControlState(selected);
  }, [phase]);

  const startGame = useCallback((startingPosition: Position = defaultPosition) => {
    if (phase !== "setup") return;
    const initial = clonePosition(startingPosition);
    const status = getGameStatus(initial);
    const reason = reasonForStatus(status);
    const nextClocks = clocked ? { white: timeControl.initialSeconds, black: timeControl.initialSeconds } : emptyClocks;
    livePositionRef.current = initial;
    setPhase(reason ? "finished" : "playing");
    setPosition(initial);
    setPositions([initial]);
    setMoves([]);
    setSelectedSquare(null);
    setPendingPromotion(null);
    setViewedPlyState(0);
    setClocks(nextClocks);
    setResult(reason ? { winner: status.kind === "checkmate" ? status.winner : null, reason, clocks: nextClocks } : null);
  }, [clocked, defaultPosition, phase, timeControl.initialSeconds]);

  const commitMove = useCallback((move: Move) => {
    const before = livePositionRef.current;
    const mover = before.turn;
    const after = applyMove(before, move);
    const status = getGameStatus(after);
    const ply = moves.length + 1;
    const record: MoveRecord = {
      ply,
      moveNumber: before.fullmoveNumber,
      color: mover,
      notation: formatMove(move, before, after),
      from: move.from,
      to: move.to,
      captured: before.board[move.to] ?? (move.isEnPassant ? { color: oppositeColor(mover), type: "pawn" } : undefined),
      promotion: move.promotion,
      position: after,
    };
    const nextClocks = cloneClocks(clocks);
    if (clocked) nextClocks[mover] += timeControl.incrementSeconds;
    livePositionRef.current = after;
    setPosition(after);
    setPositions((current) => [...current, after]);
    setMoves((current) => [...current, record]);
    setClocks(nextClocks);
    setSelectedSquare(null);
    setPendingPromotion(null);
    setViewedPlyState(ply);
    const reason = reasonForStatus(status);
    if (reason) {
      setResult({ winner: status.kind === "checkmate" ? status.winner : null, reason, clocks: nextClocks });
      setPhase("finished");
    }
  }, [clocked, clocks, moves.length, timeControl.incrementSeconds]);
  const playMove = useCallback((move: Move) => {
    if (phase !== "playing" || viewedPly !== moves.length || pendingPromotion) return;
    const legal = getLegalMoves(livePositionRef.current, move.from).find(
      (candidate) =>
        candidate.to === move.to &&
        candidate.promotion === move.promotion &&
        candidate.isCastle === move.isCastle &&
        candidate.isEnPassant === move.isEnPassant,
    );
    if (legal) commitMove(legal);
  }, [commitMove, moves.length, pendingPromotion, phase, viewedPly]);


  const selectSquare = useCallback((square: SquareIndex) => {
    if (phase !== "playing" || viewedPly !== moves.length || pendingPromotion) return;
    const current = livePositionRef.current;
    if (selectedSquare !== null) {
      const movesToSquare = getLegalMoves(current, selectedSquare).filter((move) => move.to === square);
      if (movesToSquare.length > 0) {
        if (movesToSquare.some((move) => move.promotion)) {
          setPendingPromotion({ from: selectedSquare, to: square, moves: movesToSquare });
        } else {
          commitMove(movesToSquare[0]);
        }
        return;
      }
    }
    const piece = current.board[square];
    setSelectedSquare(piece?.color === current.turn ? square : null);
  }, [commitMove, moves.length, pendingPromotion, phase, selectedSquare, viewedPly]);

  const choosePromotion = useCallback((piece: Exclude<PieceType, "king" | "pawn">) => {
    if (!pendingPromotion || phase !== "playing") return;
    const move = pendingPromotion.moves.find((candidate) => candidate.promotion === piece);
    if (move) commitMove(move);
  }, [commitMove, pendingPromotion, phase]);

  const setViewedPly = useCallback((ply: number) => {
    if (phase === "setup") return;
    setViewedPlyState(Math.max(0, Math.min(ply, moves.length)));
    setSelectedSquare(null);
    setPendingPromotion(null);
  }, [moves.length, phase]);

  const stepReplay = useCallback((direction: "backward" | "forward") => {
    if (phase === "setup") return;
    const delta = direction === "backward" ? -1 : 1;
    setViewedPlyState((current) => Math.max(0, Math.min(current + delta, moves.length)));
    setSelectedSquare(null);
    setPendingPromotion(null);
  }, [moves.length, phase]);

  const returnToLive = useCallback(() => {
    setViewedPlyState(moves.length);
    setSelectedSquare(null);
    setPendingPromotion(null);
  }, [moves.length]);

  const resign = useCallback(() => {
    if (phase !== "playing" || viewedPly !== moves.length) return;
    setResult({ winner: oppositeColor(position.turn), reason: "resignation", clocks: cloneClocks(clocks) });
    setPhase("finished");
    setSelectedSquare(null);
    setPendingPromotion(null);
  }, [clocks, moves.length, phase, position.turn, viewedPly]);

  const agreeDraw = useCallback(() => {
    if (phase !== "playing" || viewedPly !== moves.length) return;
    setResult({ winner: null, reason: "draw-agreement", clocks: cloneClocks(clocks) });
    setPhase("finished");
    setSelectedSquare(null);
    setPendingPromotion(null);
  }, [clocks, moves.length, phase, viewedPly]);

  const resetGame = useCallback((startingPosition: Position = createInitialPosition()) => {
    const initial = clonePosition(startingPosition);
    livePositionRef.current = initial;
    setPhase("setup");
    setPosition(initial);
    setPositions([initial]);
    setMoves([]);
    setSelectedSquare(null);
    setPendingPromotion(null);
    setViewedPlyState(0);
    setClocks(emptyClocks);
    setResult(null);
  }, []);

  return {
    phase,
    timeControl,
    position,
    positions,
    moves,
    selectedSquare,
    legalTargets,
    viewedPly,
    pendingPromotion,
    clocks,
    result,
    setTimeControl,
    startGame,
    selectSquare,
    playMove,
    choosePromotion,
    setViewedPly,
    stepReplay,
    returnToLive,
    resign,
    agreeDraw,
    resetGame,
  };
}

export function checkedKingSquare(position: Position): SquareIndex | null {
  if (!isInCheck(position, position.turn)) return null;
  const king = position.board.findIndex((piece) => piece?.color === position.turn && piece.type === "king");
  return king >= 0 ? king : null;
}
