import type { MoveRecord } from "../../domain/chess/types";

type MoveListProps = {
  moves: MoveRecord[];
  viewedPly: number;
  livePly: number;
  onSelectPly: (ply: number) => void;
};

export function MoveList({ moves, viewedPly, livePly, onSelectPly }: MoveListProps) {
  const rows = Array.from({ length: Math.ceil(moves.length / 2) }, (_, index) => {
    const white = moves[index * 2];
    const black = moves[index * 2 + 1];
    return { moveNumber: index + 1, white, black };
  });
  const isLive = viewedPly === livePly;
  return (
    <section className="move-list-panel" aria-label="Move list">
      <div className="move-list-heading">
        <h2>Moves</h2>
        {!isLive && <button className="replay-return" type="button" onClick={() => onSelectPly(livePly)}>Return to current</button>}
      </div>
      <div className="move-list" tabIndex={0}>
        {rows.length === 0 && <p className="move-list-empty">Moves will appear here.</p>}
        {rows.map(({ moveNumber, white, black }) => (
          <div className="move-row" key={moveNumber}>
            <span className="move-number">{moveNumber}.</span>
            <button
              type="button"
              className={`move-button ${white && viewedPly === white.ply ? "selected" : ""}`}
              aria-label={`Move ${moveNumber}, White ${white?.notation ?? "not played"}`}
              aria-current={white && viewedPly === white.ply ? "step" : undefined}
              disabled={!white}
              onClick={() => white && onSelectPly(white.ply)}
            >
              {white?.notation ?? "—"}
            </button>
            <button
              type="button"
              className={`move-button ${black && viewedPly === black.ply ? "selected" : ""}`}
              aria-label={`Move ${moveNumber}, Black ${black?.notation ?? "not played"}`}
              aria-current={black && viewedPly === black.ply ? "step" : undefined}
              disabled={!black}
              onClick={() => black && onSelectPly(black.ply)}
            >
              {black?.notation ?? "—"}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
