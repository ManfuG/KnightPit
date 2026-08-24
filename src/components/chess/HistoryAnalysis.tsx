import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { clonePosition } from "../../domain/chess/engine";
import type { HistoryEntry } from "../../domain/chess/history";
import { checkedKingSquare } from "../../hooks/useChessGame";
import { useReplayKeyboard } from "../../hooks/useReplayKeyboard";
import { CapturedMaterial } from "./CapturedMaterial";
import { ChessBoard } from "./ChessBoard";
import { GameResult } from "./GameResult";
import { Panel } from "../ui/Primitives";

export function HistoryAnalysis({ entry }: { entry: HistoryEntry }) {
  const navigate = useNavigate();
  const positions = useMemo(
    () => [clonePosition(entry.startingPosition), ...entry.moves.map((move) => clonePosition(move.position))],
    [entry],
  );
  const [viewedPly, setViewedPly] = useState(entry.moves.length);
  const stepReplay = useCallback((direction: "backward" | "forward") => {
    setViewedPly((current) => Math.max(0, Math.min(current + (direction === "backward" ? -1 : 1), entry.moves.length)));
  }, [entry.moves.length]);
  useReplayKeyboard({ phase: "playing", stepReplay });

  const viewedPosition = positions[viewedPly] ?? positions[0];
  const lastRecord = viewedPly > 0 ? entry.moves[viewedPly - 1] : undefined;
  const lastMove = lastRecord ? { from: lastRecord.from, to: lastRecord.to, promotion: lastRecord.promotion } : null;

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">History analysis · {entry.mode === "play" ? `Play · ${entry.timeControl}` : "Training · Untimed"}</p>
          <h1>Review the position.</h1>
        </div>
      </header>
      <div className="history-analysis-layout">
        <div className="game-board-column">
          <Panel className="board-stage game-board-stage history-analysis-board">
            <div className="board-frame">
              <ChessBoard
                orientation="white"
                position={viewedPosition}
                selectedSquare={null}
                legalTargets={[]}
                lastMove={lastMove}
                checkedKing={checkedKingSquare(viewedPosition)}
                interactive={false}
                ariaLabel="Historical chess board"
              />
            </div>
          </Panel>
        </div>
        <aside className="history-analysis-side">
          <CapturedMaterial moves={entry.moves} viewedPly={viewedPly} />
          <GameResult
            result={entry.result}
            playerColor={entry.playerColor}
            moves={entry.moves}
            viewedPly={viewedPly}
            onNewGame={() => navigate("/history")}
            onSelectPly={setViewedPly}
            newGameLabel="Back to history"
          />
        </aside>
      </div>
    </>
  );
}
