from __future__ import annotations

from dataclasses import dataclass, replace as dataclass_replace

from .board import BoardState, ChessEnvironment, Color, Move, parse_square


@dataclass(frozen=True)
class RewardProfile:
    name: str = "principles-v1"
    opening_plies: int = 20
    material_weight: float = 0.55
    center_weight: float = 0.30
    development_weight: float = 0.15
    terminal_win: float = 1.0
    terminal_loss: float = -1.0
    draw: float = 0.0
    mcts_heuristic_weight: float = 0.20
    schedule_version: str = "principles-v1-schedule-1"

    @classmethod
    def for_iteration(cls, iteration: int) -> "RewardProfile":
        if iteration < 1:
            raise ValueError("iteration must be positive")
        base = cls()
        center_scale = max(0.0, min(1.0, (12 - iteration) / 11.0))
        if iteration <= 4:
            development_scale = 1.0
            heuristic_weight = 0.20
        elif iteration <= 8:
            development_scale = 0.5
            heuristic_weight = 0.10
        else:
            development_scale = 0.0
            heuristic_weight = 0.0
        return dataclass_replace(
            base,
            center_weight=base.center_weight * center_scale,
            development_weight=base.development_weight * development_scale,
            mcts_heuristic_weight=heuristic_weight,
        )


@dataclass(frozen=True)
class PositionEvaluation:
    material: float
    center: float
    development: float
    potential: float


@dataclass(frozen=True)
class TransitionEvaluation:
    before: PositionEvaluation
    after: PositionEvaluation
    material_delta: float
    captured_value: float


class RewardEvaluator:
    _VALUES = {"pawn": 1.0, "knight": 3.0, "bishop": 3.0, "rook": 5.0, "queen": 9.0, "king": 0.0}
    _CENTER = frozenset(parse_square(square) for square in ("d4", "e4", "d5", "e5"))
    _INITIAL_MINOR_SQUARES = {
        "white": frozenset(parse_square(square) for square in ("b1", "g1", "c1", "f1")),
        "black": frozenset(parse_square(square) for square in ("b8", "g8", "c8", "f8")),
    }

    def __init__(self, profile: RewardProfile | None = None) -> None:
        self.profile = profile or RewardProfile()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(-1.0, min(1.0, float(value)))

    def _material(self, board: BoardState, perspective: Color) -> float:
        score = sum(
            (1.0 if piece.color == perspective else -1.0) * self._VALUES[piece.kind]
            for piece in board.piece_map().values()
        )
        return self._clamp(score / 39.0)

    def _center(self, board: BoardState, perspective: Color) -> float:
        score = 0.0
        for square, piece in board.piece_map().items():
            if square in self._CENTER:
                score += 1.0 if piece.color == perspective else -1.0
        opponent: Color = "black" if perspective == "white" else "white"
        own_board = dataclass_replace(board, turn=perspective)
        opponent_board = dataclass_replace(board, turn=opponent)
        own_destinations = sum(1 for move in own_board.legal_moves() if move.to_square in self._CENTER)
        opponent_destinations = sum(1 for move in opponent_board.legal_moves() if move.to_square in self._CENTER)
        score += 0.5 * (own_destinations - opponent_destinations)
        return self._clamp(score / 6.0)

    def _development(self, board: BoardState, perspective: Color, ply: int) -> float:
        if ply > self.profile.opening_plies:
            return 0.0
        developed = {"white": 0, "black": 0}
        for square, piece in board.piece_map().items():
            if piece.kind in ("knight", "bishop") and square not in self._INITIAL_MINOR_SQUARES[piece.color]:
                developed[piece.color] += 1
        return self._clamp((developed[perspective] - developed["black" if perspective == "white" else "white"]) / 4.0)

    def evaluate_position(self, board: BoardState, perspective: Color, ply: int) -> PositionEvaluation:
        material = self._material(board, perspective)
        center = self._center(board, perspective)
        development = self._development(board, perspective, ply)
        potential = self._clamp(
            self.profile.material_weight * material
            + self.profile.center_weight * center
            + self.profile.development_weight * development
        )
        return PositionEvaluation(material, center, development, potential)

    def evaluate_transition(
        self,
        before: BoardState,
        after: BoardState,
        move: Move,
        perspective: Color,
        ply: int,
    ) -> TransitionEvaluation:
        before_eval = self.evaluate_position(before, perspective, ply)
        after_eval = self.evaluate_position(after, perspective, ply + 1)
        captured_value = 0.0
        captured = before.piece_at(move.to_square)
        if captured is not None and captured.color != perspective:
            captured_value = self._VALUES[captured.kind]
        elif move.is_en_passant:
            direction = -1 if before.turn == "white" else 1
            captured = before.piece_at(move.to_square - 8 * direction)
            if captured is not None and captured.color != perspective:
                captured_value = self._VALUES[captured.kind]
        return TransitionEvaluation(
            before_eval,
            after_eval,
            self._clamp(after_eval.material - before_eval.material),
            float(captured_value),
        )

    def terminal_target(self, environment: ChessEnvironment, perspective: Color) -> float:
        if not environment.is_terminal():
            raise ValueError("terminal_target requires a terminal environment")
        status = environment.status()
        if status.kind == "checkmate":
            if status.winner == perspective:
                return self.profile.terminal_win
            return self.profile.terminal_loss
        return self.profile.draw
