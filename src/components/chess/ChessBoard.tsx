import { type Color, type Move, type Position, type SquareIndex, squareName } from "../../domain/chess/types";
export type ChessBoardProps = {
  position: Position;
  orientation?: Color;
  selectedSquare: SquareIndex | null;
  legalTargets: SquareIndex[];
  lastMove: Move | null;
  checkedKing: SquareIndex | null;
  interactive: boolean;
  ariaLabel: string;
  onSquareClick?: (square: SquareIndex) => void;
};

export type PieceGlyphType = NonNullable<Position["board"][number]>["type"];

export const PIECE_GLYPHS: Record<PieceGlyphType, string> = {
  king: "K",
  queen: "Q",
  rook: "R",
  bishop: "B",
  knight: "N",
  pawn: "P",
};

export function PieceGlyph({ type, color }: { type: PieceGlyphType; color: Color }) {
  const side = color === "white" ? "w" : "b";
  return <img className="piece-svg" src={`/pieces/spatial/${side}${PIECE_GLYPHS[type]}.svg`} alt="" aria-hidden="true" draggable={false} />;
}

const files = ["a", "b", "c", "d", "e", "f", "g", "h"];

export function ChessBoard({ position, orientation = "white", selectedSquare, legalTargets, lastMove, checkedKing, interactive, ariaLabel, onSquareClick }: ChessBoardProps) {
  const legalTargetSet = new Set(legalTargets);
  return (
    <div className="board" role="grid" aria-label={ariaLabel}>
      {Array.from({ length: 64 }, (_, visualSquare) => {
        const visualRank = Math.floor(visualSquare / 8);
        const visualFile = visualSquare % 8;
        const canonicalRank = orientation === "black" ? 7 - visualRank : visualRank;
        const canonicalFile = orientation === "black" ? 7 - visualFile : visualFile;
        const canonicalSquare = canonicalRank * 8 + canonicalFile;
        const piece = position.board[canonicalSquare];
        const name = squareName(canonicalSquare);
        const isDark = (canonicalRank + canonicalFile) % 2 === 1;
        const isSelected = selectedSquare === canonicalSquare;
        const isTarget = legalTargetSet.has(canonicalSquare);
        const isLastMove = lastMove?.from === canonicalSquare || lastMove?.to === canonicalSquare;
        const isCheckedKing = checkedKing === canonicalSquare;
        const description = piece ? `${piece.color} ${piece.type}` : "empty";
        const state = [
          "square",
          isDark ? "dark" : "light",
          isSelected ? "selected" : "",
          isTarget ? "legal-target" : "",
          isLastMove ? "last-move" : "",
          isCheckedKing ? "checked-king" : "",
        ].filter(Boolean).join(" ");
        return (
          <button
            key={name}
            type="button"
            className={state}
            role="gridcell"
            data-square={name}
            aria-label={`${name}, ${description}${isTarget ? ", legal target" : ""}`}
            aria-pressed={isSelected}
            disabled={!interactive}
            onClick={() => onSquareClick?.(canonicalSquare)}
          >
            {piece && <span className={`piece piece-${piece.color}`}><PieceGlyph type={piece.type} color={piece.color} /></span>}
            {visualFile === 0 && <span className="coordinate" aria-hidden="true">{8 - canonicalRank}</span>}
            {visualRank === 7 && <span className="coordinate file-coordinate" aria-hidden="true">{files[canonicalFile]}</span>}
          </button>
        );
      })}
    </div>
  );
}
