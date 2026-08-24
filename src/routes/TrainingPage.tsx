import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CapturedMaterial } from "../components/chess/CapturedMaterial";
import { ChessBoard, PieceGlyph } from "../components/chess/ChessBoard";
import { HistoryAnalysis } from "../components/chess/HistoryAnalysis";
import { GameResult } from "../components/chess/GameResult";
import { MoveList } from "../components/chess/MoveList";
import { LinkButton, Button, Panel } from "../components/ui/Primitives";
import { clonePosition, createInitialPosition } from "../domain/chess/engine";
import { getGameHistory } from "../domain/chess/history";
import { formatFEN, parseFEN, validatePosition } from "../domain/chess/fen";
import type { CastlingRights, Color, PieceType, Position, SquareIndex } from "../domain/chess/types";
import { checkedKingSquare, useChessGame } from "../hooks/useChessGame";
import { useReplayKeyboard } from "../hooks/useReplayKeyboard";

type PaletteSelection = { color: Color; type: PieceType } | "eraser";
type TrainingMode = "editing" | "continuation";

const palette: Array<{ color: Color; type: PieceType }> = [
  { color: "white", type: "king" }, { color: "white", type: "queen" }, { color: "white", type: "rook" },
  { color: "white", type: "bishop" }, { color: "white", type: "knight" }, { color: "white", type: "pawn" },
  { color: "black", type: "king" }, { color: "black", type: "queen" }, { color: "black", type: "rook" },
  { color: "black", type: "bishop" }, { color: "black", type: "knight" }, { color: "black", type: "pawn" },
];

const castlingLabels: Array<{ key: keyof CastlingRights; label: string }> = [
  { key: "whiteKingside", label: "White king-side" },
  { key: "whiteQueenside", label: "White queen-side" },
  { key: "blackKingside", label: "Black king-side" },
  { key: "blackQueenside", label: "Black queen-side" },
];

function normalizeCastling(position: Position): void {
  const has = (square: SquareIndex, color: Color, type: PieceType) => position.board[square]?.color === color && position.board[square]?.type === type;
  position.castling.whiteKingside = position.castling.whiteKingside && has(60, "white", "king") && has(63, "white", "rook");
  position.castling.whiteQueenside = position.castling.whiteQueenside && has(60, "white", "king") && has(56, "white", "rook");
  position.castling.blackKingside = position.castling.blackKingside && has(4, "black", "king") && has(7, "black", "rook");
  position.castling.blackQueenside = position.castling.blackQueenside && has(4, "black", "king") && has(0, "black", "rook");
}

export function TrainingPage() {
  const game = useChessGame({ clocked: false });
  const [searchParams] = useSearchParams();
  const historyId = searchParams.get("history");
  const historyEntry = historyId ? getGameHistory(historyId) : null;
  const [mode, setMode] = useState<TrainingMode>("editing");
  const [draft, setDraft] = useState<Position>(() => createInitialPosition());
  const [selection, setSelection] = useState<PaletteSelection>({ color: "white", type: "pawn" });
  const [boardOrientation, setBoardOrientation] = useState<Color>("white");
  const [fenText, setFenText] = useState(() => formatFEN(createInitialPosition()));
  const [fenError, setFenError] = useState<string | null>(null);
  const boardAnchorRef = useRef<HTMLDivElement>(null);
  const centerAfterStartRef = useRef(false);
  useReplayKeyboard({ phase: mode === "editing" ? "setup" : game.phase, stepReplay: game.stepReplay });

  useEffect(() => {
    if (game.phase === "setup" || !centerAfterStartRef.current) return;
    boardAnchorRef.current?.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" });
    centerAfterStartRef.current = false;
  }, [game.phase]);

  const draftValidation = validatePosition(draft);
  const isLive = game.viewedPly === game.moves.length;
  const viewedPosition = game.positions[game.viewedPly] ?? game.position;
  const lastRecord = game.viewedPly > 0 ? game.moves[game.viewedPly - 1] : undefined;
  const lastMove = lastRecord ? { from: lastRecord.from, to: lastRecord.to, promotion: lastRecord.promotion } : null;
  const boardIsInteractive = mode === "continuation" && game.phase === "playing" && isLive && !game.pendingPromotion;

  const updateDraft = (change: (next: Position) => void) => {
    const next = clonePosition(draft);
    change(next);
    normalizeCastling(next);
    next.enPassant = null;
    setDraft(next);
    setFenText(formatFEN(next));
    setFenError(null);
  };

  const handleEditorSquare = (square: SquareIndex) => {
    updateDraft((next) => {
      next.board[square] = selection === "eraser" ? null : { ...selection };
    });
  };

  const handleLoadFEN = () => {
    try {
      const parsed = parseFEN(fenText);
      const validation = validatePosition(parsed);
      if (!validation.valid) {
        setFenError(validation.error);
        return;
      }
      const next = clonePosition(parsed);
      setDraft(next);
      setFenText(formatFEN(next));
      setFenError(null);
    } catch (error) {
      setFenError(error instanceof Error ? error.message : "Invalid FEN");
    }
  };

  const resetDraft = () => {
    const next = createInitialPosition();
    setDraft(next);
    setFenText(formatFEN(next));
    setFenError(null);
  };

  const clearDraft = () => {
    updateDraft((next) => {
      next.board = Array.from({ length: 64 }, () => null);
    });
  };

  const startTraining = () => {
    if (!draftValidation.valid) return;
    centerAfterStartRef.current = true;
    game.startGame(clonePosition(draft));
    setMode("continuation");
  };

  const backToSetup = () => {
    game.resetGame();
    setMode("editing");
  };
  const resetTrainingPosition = () => {
    game.resetGame(clonePosition(draft));
    setMode("editing");
  };

  const finishToSetup = () => {
    game.resetGame();
    setMode("editing");
  };

  const rotateBoard = () => {
    setBoardOrientation((current) => current === "white" ? "black" : "white");
  };
  if (historyId) {
    if (historyEntry) return <HistoryAnalysis entry={historyEntry} />;
    return (
      <>
        <header className="page-header">
          <div>
            <p className="eyebrow">History analysis</p>
            <h1>That game is unavailable.</h1>
          </div>
        </header>
        <Panel className="history-error-panel" as="section" aria-label="History entry unavailable">
          <h2>History entry not found</h2>
          <p>This record may have been cleared from local browser storage.</p>
          <LinkButton to="/history" variant="primary">Back to history</LinkButton>
        </Panel>
      </>
    );
  }

  return (
    <>
      <header className={`page-header ${mode === "editing" ? "page-header-compact" : ""}`}>
        <div>
          <p className="eyebrow">Study room</p>
          {mode !== "editing" && <h1>{game.phase === "finished" ? "Study the result." : "Continue the position."}</h1>}
        </div>
      </header>

      {mode === "editing" ? (
        <div className="training-grid">
          <div className="board-layout">
            <Panel className="board-stage">
              <div className="board-frame">
                <ChessBoard
                  orientation={boardOrientation}
                  position={draft}
                  selectedSquare={null}
                  legalTargets={[]}
                  lastMove={null}
                  checkedKing={null}
                  interactive
                  ariaLabel="Training position editor board"
                  onSquareClick={handleEditorSquare}
                />
              </div>
            </Panel>
            <Panel className="actions-bar">
              <Button variant="secondary" onClick={clearDraft}>Clear board</Button>
              <Button variant="secondary" onClick={resetDraft}>Reset starting position</Button>
              <Button variant="secondary" onClick={rotateBoard}>Rotate board</Button>
              <div className="action-row">
                <Button variant="secondary" onClick={handleLoadFEN}>Load FEN</Button>
                <Button variant="primary" onClick={startTraining} disabled={!draftValidation.valid}>Play position</Button>
              </div>
            </Panel>
          </div>

          <Panel className="setup-panel" as="aside">
            <h2>Position setup</h2>
            <fieldset className="field palette-field">
              <legend>Piece palette</legend>
              <div className="piece-palette" aria-label="Piece palette">
                {palette.map((piece) => {
                  const isSelected = selection !== "eraser" && selection.color === piece.color && selection.type === piece.type;
                  return (
                    <button
                      key={`${piece.color}-${piece.type}`}
                      type="button"
                      className="palette-piece"
                      aria-label={`${piece.color} ${piece.type}`}
                      aria-pressed={isSelected}
                      onClick={() => setSelection(piece)}
                    >
                      <span className={`piece piece-${piece.color}`}><PieceGlyph type={piece.type} color={piece.color} /></span>
                    </button>
                  );
                })}
                <button type="button" className="palette-piece palette-eraser" aria-pressed={selection === "eraser"} onClick={() => setSelection("eraser")}>×</button>
              </div>
            </fieldset>

            <fieldset className="field">
              <legend>Side to move</legend>
              <div className="radio-row">
                {(["white", "black"] as const).map((color) => (
                  <label className="radio-choice" key={color}>
                    <input type="radio" name="training-side" checked={draft.turn === color} onChange={() => updateDraft((next) => { next.turn = color; })} />
                    {color === "white" ? "White" : "Black"}
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset className="field castling-field">
              <legend>Castling rights</legend>
              {castlingLabels.map(({ key, label }) => (
                <label className="checkbox-choice" key={key}>
                  <input type="checkbox" checked={draft.castling[key]} onChange={(event) => updateDraft((next) => { next.castling[key] = event.target.checked; })} />
                  {label}
                </label>
              ))}
            </fieldset>

            <div className="field">
              <label htmlFor="training-fen">FEN</label>
              <input className="input" id="training-fen" value={fenText} onChange={(event) => { setFenText(event.target.value); setFenError(null); }} aria-invalid={Boolean(fenError)} aria-describedby={fenError ? "training-fen-error" : undefined} />
              {fenError && <p className="field-error" id="training-fen-error" role="alert">{fenError}</p>}
            </div>
            {!draftValidation.valid && <p className="field-error" role="alert">{draftValidation.error}</p>}
          </Panel>
        </div>
      ) : (
        <div className="training-grid training-continuation">
          <div className="board-layout">
            <Panel className="board-stage game-board-stage">
              <div className="board-frame" ref={boardAnchorRef}>
                <ChessBoard
                  orientation={boardOrientation}
                  position={viewedPosition}
                  selectedSquare={boardIsInteractive ? game.selectedSquare : null}
                  legalTargets={boardIsInteractive ? game.legalTargets : []}
                  lastMove={lastMove}
                  checkedKing={checkedKingSquare(viewedPosition)}
                  interactive={boardIsInteractive}
                  ariaLabel="Training continuation board"
                  onSquareClick={game.selectSquare}
                />
                {game.pendingPromotion && (
                  <div className="promotion-chooser" aria-label="Choose promotion piece">
                    <span>Promote to</span>
                    {game.pendingPromotion.moves.map((move) => (
                      <button key={move.promotion} type="button" className="promotion-choice" onClick={() => move.promotion && game.choosePromotion(move.promotion)}>{move.promotion}</button>
                    ))}
                  </div>
                )}
              </div>
            </Panel>
          </div>
          <Panel className="setup-panel training-controls" as="aside">
            {game.phase === "finished" && game.result ? (
              <GameResult result={game.result} moves={game.moves} viewedPly={game.viewedPly} onNewGame={finishToSetup} onSelectPly={game.setViewedPly} />
            ) : (
              <>
                <CapturedMaterial moves={game.moves} viewedPly={game.viewedPly} />
                <MoveList moves={game.moves} viewedPly={game.viewedPly} livePly={game.moves.length} onSelectPly={game.setViewedPly} />
                <div className="training-action-row">
                  <Button variant="secondary" onClick={backToSetup}>Back to position setup</Button>
                  <Button variant="quiet" onClick={resetTrainingPosition}>Reset position</Button>
                </div>
              </>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
