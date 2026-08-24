from __future__ import annotations

from typing import Mapping

import numpy as np

from .board import BoardState, Color, Move, PieceKind

# 12 piece planes, side-to-move, four castling rights, en-passant target.
ENCODING_SHAPE = (18, 8, 8)
PROMOTION_CODES: dict[PieceKind | None, int] = {None: 0, "knight": 1, "bishop": 2, "rook": 3, "queen": 4}
PROMOTION_FROM_CODE = {value: key for key, value in PROMOTION_CODES.items()}
MOVE_SPACE_SIZE = 64 * 64 * 5
_PIECE_PLANES: dict[tuple[Color, PieceKind], int] = {
    ("white", "pawn"): 0, ("white", "knight"): 1,
    ("white", "bishop"): 2, ("white", "rook"): 3,
    ("white", "queen"): 4, ("white", "king"): 5,
    ("black", "pawn"): 6, ("black", "knight"): 7,
    ("black", "bishop"): 8, ("black", "rook"): 9,
    ("black", "queen"): 10, ("black", "king"): 11,
}


def encode_board(board: BoardState) -> np.ndarray:
    """Return a deterministic float32 tensor indexed rank 8 to rank 1."""
    encoded = np.zeros(ENCODING_SHAPE, dtype=np.float32)
    for square, piece in board.piece_map().items():
        plane = _PIECE_PLANES[(piece.color, piece.kind)]
        encoded[plane, square // 8, square % 8] = 1.0
    encoded[12, :, :] = 1.0 if board.turn == "white" else 0.0
    encoded[13, :, :] = float(board.white_kingside)
    encoded[14, :, :] = float(board.white_queenside)
    encoded[15, :, :] = float(board.black_kingside)
    encoded[16, :, :] = float(board.black_queenside)
    if board.ep_square is not None:
        encoded[17, board.ep_square // 8, board.ep_square % 8] = 1.0
    return encoded


def move_to_index(move: Move) -> int:
    return ((move.from_square * 64) + move.to_square) * 5 + PROMOTION_CODES.get(move.promotion, 0)


def index_to_move(index: int) -> Move:
    if not 0 <= index < MOVE_SPACE_SIZE:
        raise ValueError(f"move index outside space: {index}")
    base, promotion_code = divmod(index, 5)
    from_square, to_square = divmod(base, 64)
    return Move(from_square, to_square, promotion=PROMOTION_FROM_CODE[promotion_code])


def legal_policy(board: BoardState, logits: np.ndarray, temperature: float = 1.0) -> dict[str, float]:
    """Softmax logits over legal moves only, returned with UCI keys."""
    legal = board.legal_moves()
    if not legal:
        return {}
    values = np.asarray([logits[move_to_index(move)] for move in legal], dtype=np.float64)
    if temperature <= 0:
        result = {move.uci(): 0.0 for move in legal}
        result[legal[int(np.argmax(values))].uci()] = 1.0
        return result
    values = values / temperature
    values -= np.max(values)
    weights = np.exp(np.clip(values, -60.0, 60.0))
    weights /= np.sum(weights)
    return {move.uci(): float(weight) for move, weight in zip(legal, weights)}


def policy_vector(policy: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(0.0, value) for value in policy.values())
    if total <= 0:
        return dict(policy)
    return {move: max(0.0, value) / total for move, value in policy.items()}
