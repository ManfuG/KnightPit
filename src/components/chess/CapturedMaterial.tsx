import { PIECE_VALUES } from "../../domain/chess/engine";
import type { Color, MoveRecord } from "../../domain/chess/types";
import { PieceGlyph } from "./ChessBoard";

type CapturedMaterialProps = {
  moves: MoveRecord[];
  viewedPly: number;
};

export function CapturedMaterial({ moves, viewedPly }: CapturedMaterialProps) {
  const capturedByColor: Record<Color, MoveRecord["captured"][]> = { white: [], black: [] };
  for (const move of moves.slice(0, viewedPly)) {
    if (move.captured) capturedByColor[move.color].push(move.captured);
  }

  return (
    <section className="captured-material" aria-label="Captured material">
      <h2>Material</h2>
      {(["white", "black"] as const).map((color) => {
        const pieces = capturedByColor[color].filter((piece): piece is NonNullable<MoveRecord["captured"]> => Boolean(piece));
        const points = pieces.reduce((total, piece) => total + PIECE_VALUES[piece.type], 0);
        const label = `${color === "white" ? "White" : "Black"} captured ${pieces.length} piece${pieces.length === 1 ? "" : "s"} for ${points} point${points === 1 ? "" : "s"}`;
        return (
          <div className="captured-row" key={color} aria-label={label}>
            <span className="captured-color">{color === "white" ? "White" : "Black"}</span>
            <span className="captured-pieces" aria-label={pieces.length > 0 ? pieces.map((piece) => `${piece.color} ${piece.type}`).join(", ") : "No captures"}>
              {pieces.length > 0 ? pieces.map((piece, index) => <span className={`captured-piece piece piece-${piece.color}`} key={`${piece.color}-${piece.type}-${index}`} aria-hidden="true"><PieceGlyph type={piece.type} color={piece.color} /></span>) : <span className="captured-empty">—</span>}
            </span>
            <strong className="captured-points">{points}</strong>
          </div>
        );
      })}
    </section>
  );
}
