import { useEffect, useRef } from "react";
import { ChessBoard } from "../components/chess/ChessBoard";
import { CapturedMaterial } from "../components/chess/CapturedMaterial";
import { ClockPanel } from "../components/chess/ClockPanel";
import { GameResult } from "../components/chess/GameResult";
import { MoveList } from "../components/chess/MoveList";
import { Button, Panel } from "../components/ui/Primitives";
import { checkedKingSquare, TIME_CONTROLS } from "../hooks/useChessGame";
import { useChessVsAi } from "../hooks/useChessVsAi";
import { useReplayKeyboard } from "../hooks/useReplayKeyboard";
import type { Move } from "../domain/chess/types";
import { useRecordCompletedGame } from "../hooks/useRecordCompletedGame";
export function PlayPage() {
  const game = useChessVsAi({ clocked: true });
  const boardAnchorRef = useRef<HTMLDivElement>(null);
  const centerAfterStartRef = useRef(false);
  useRecordCompletedGame(game, "play", game.timeControl.label, game.playerColor);
  useReplayKeyboard({ phase: game.phase, stepReplay: game.stepReplay });
  const isLive = game.viewedPly === game.moves.length;
  const viewedPosition = game.positions[game.viewedPly] ?? game.position;
  const lastRecord = game.viewedPly > 0 ? game.moves[game.viewedPly - 1] : undefined;
  const lastMove: Move | null = lastRecord ? { from: lastRecord.from, to: lastRecord.to, promotion: lastRecord.promotion } : null;
  const boardIsInteractive = game.phase === "playing" && game.position.turn === game.playerColor && game.aiStatus !== "thinking" && isLive && !game.pendingPromotion;
  const checkedKing = checkedKingSquare(viewedPosition);

  useEffect(() => {
    if (game.phase === "setup" || !centerAfterStartRef.current) return;
    boardAnchorRef.current?.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" });
    centerAfterStartRef.current = false;
  }, [game.phase]);

  const startGame = () => {
    centerAfterStartRef.current = true;
    game.startGame();
  };

  if (game.phase === "setup") {
    return (
      <>
        <header className="page-header page-header-compact">
          <div>
            <p className="eyebrow">Play room</p>
          </div>
        </header>
        <section className="game-setup" aria-label="Game setup">
          <div className="setup-controls">
            <span className="nav-label">Time control</span>
            <div className="controls-row">
              {TIME_CONTROLS.map((control) => (
                <button key={control.label} type="button" className="time-control" aria-pressed={game.timeControl.label === control.label} onClick={() => game.setTimeControl(control.label)}>
                  {control.label}
                </button>
              ))}
            </div>
          </div>
          <Panel className="play-workspace">
            <ChessBoard
              orientation={game.playerColor}
              position={game.position}
              selectedSquare={null}
              legalTargets={[]}
              lastMove={null}
              checkedKing={null}
              interactive={false}
              ariaLabel="Play board starting position"
              onSquareClick={game.selectSquare}
            />
            <div className="setup-summary">
              <h2>
                <span>{game.timeControl.label}</span>
                <span className="setup-summary-subtitle">You vs KnightPit AI</span>
              </h2>
              <Button variant="primary" icon="play" onClick={startGame}>Start game</Button>
            </div>
          </Panel>
        </section>
      </>
    );
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Play room · {game.timeControl.label} · {game.playerColor === "white" ? "White" : "Black"}</p>
          <h1>{game.phase === "finished" ? "The game is complete." : "Stay with the position."}</h1>
        </div>
      </header>

      <div className={`game-layout ${game.phase === "finished" ? "game-finished" : ""}`}>
        <div className="game-board-column">
          <Panel className="board-stage game-board-stage">
            <div className="board-frame" ref={boardAnchorRef}>
              <ChessBoard
                orientation={game.playerColor}
                position={viewedPosition}
                selectedSquare={boardIsInteractive ? game.selectedSquare : null}
                legalTargets={boardIsInteractive ? game.legalTargets : []}
                lastMove={lastMove}
                checkedKing={checkedKing}
                interactive={boardIsInteractive}
                ariaLabel="Live chess board"
                onSquareClick={game.selectSquare}
              />
              {game.pendingPromotion && (
                <div className="promotion-chooser" aria-label="Choose promotion piece">
                  <span>Promote to</span>
                  {game.pendingPromotion.moves.map((move) => (
                    <button key={move.promotion} type="button" className="promotion-choice" onClick={() => move.promotion && game.choosePromotion(move.promotion)}>
                      {move.promotion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </Panel>
        </div>

        <aside className="game-side-column">
          <ClockPanel clocks={game.clocks} turn={game.position.turn} phase={game.phase} resultReason={game.result?.reason === "timeout" ? "Time" : undefined} />
          <CapturedMaterial moves={game.moves} viewedPly={game.viewedPly} />
          {game.phase === "finished" && game.result ? (
            <GameResult result={game.result} playerColor={game.playerColor} moves={game.moves} viewedPly={game.viewedPly} onNewGame={() => game.resetGame()} onSelectPly={game.setViewedPly} />
          ) : (
            <Panel className="side-panel game-controls-panel" as="section">
              {(game.aiStatus !== "idle" || game.aiError || game.aiEvaluation !== null) && (
                <p role={game.aiStatus === "error" || game.aiError ? "alert" : "status"}>
                  {game.aiStatus === "thinking" ? "Thinking…" : game.aiError ?? `AI ${game.aiEvaluation?.toFixed(2)}`}
                </p>
              )}
              <MoveList moves={game.moves} viewedPly={game.viewedPly} livePly={game.moves.length} onSelectPly={game.setViewedPly} />
              <div className="game-action-row">
                <Button variant="secondary" onClick={game.resign} disabled={!isLive}>Resign</Button>
                <Button variant="ghost" onClick={game.agreeDraw} disabled={!isLive}>Offer draw</Button>
                <Button variant="quiet" onClick={() => game.resetGame()}>New game</Button>
              </div>
            </Panel>
          )}
        </aside>
      </div>
    </>
  );
}
