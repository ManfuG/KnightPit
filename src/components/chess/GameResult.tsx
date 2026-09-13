import type { Color, GameResult as ChessGameResult, MoveRecord } from "../../domain/chess/types";
import { Button } from "../ui/Primitives";
import { MoveList } from "./MoveList";

type GameResultProps = {
  result: ChessGameResult;
  playerColor?: Color;
  moves: MoveRecord[];
  viewedPly: number;
  onNewGame: () => void;
  onSelectPly: (ply: number) => void;
  newGameLabel?: string;
};

const reasonLabels: Record<ChessGameResult["reason"], string> = {
  checkmate: "Checkmate",
  timeout: "Time",
  resignation: "Resignation",
  "draw-agreement": "Draw by agreement",
  stalemate: "Stalemate",
  "insufficient-material": "Insufficient material",
};

export function GameResult({ result, playerColor, moves, viewedPly, onNewGame, onSelectPly, newGameLabel = "New game" }: GameResultProps) {
  const winner = result.winner
    ? playerColor ? (result.winner === playerColor ? "User wins" : "AI wins") : `${result.winner === "white" ? "White" : "Black"} wins`
    : "Draw";
  return (
    <section className="result-panel" aria-labelledby="game-result-title">
      <div className="result-heading">
        <p className="eyebrow">Game complete</p>
        <h2 id="game-result-title">{winner}</h2>
        <p className="result-reason">{reasonLabels[result.reason]}</p>
      </div>
      <MoveList moves={moves} viewedPly={viewedPly} livePly={moves.length} onSelectPly={onSelectPly} showTimes />
      <Button className="w-full" variant="primary" icon="play" onClick={onNewGame}>{newGameLabel}</Button>
    </section>
  );
}
