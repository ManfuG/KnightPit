from __future__ import annotations

import random
from dataclasses import dataclass

from .board import ChessEnvironment
from .encoding import encode_board
from .replay_buffer import ReplayExample
from .reward import RewardEvaluator


@dataclass(frozen=True)
class TacticalCase:
    name: str
    category: str
    fen: str
    expected_moves: tuple[str, ...]


_CASES: tuple[TacticalCase, ...] = (
    TacticalCase("mate-1-queen-g7", "mate-in-one", "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1", ("f7g7",)),
    TacticalCase("mate-1-queen-h7", "mate-in-one", "7k/6Q1/6K1/8/8/8/8/8 w - - 0 1", ("g7h7",)),
    TacticalCase("mate-1-queen-e7", "mate-in-one", "5k2/5Q2/6K1/8/8/8/8/8 w - - 0 1", ("g6f6",)),
    TacticalCase("mate-1-queen-g6", "mate-in-one", "6k1/6Q1/5K2/8/8/8/8/8 w - - 0 1", ("f6g6",)),
    TacticalCase("mate-1-queen-g7-alt", "mate-in-one", "7k/4Q3/5K2/8/8/8/8/8 w - - 0 1", ("e7g7",)),
    TacticalCase("mate-1-queen-b7", "mate-in-one", "k7/Q7/2K5/8/8/8/8/8 w - - 0 1", ("a7b7",)),
    TacticalCase("capture-queen", "material-capture", "6k1/8/8/8/8/8/3q4/3QK3 w - - 0 1", ("d1d2",)),
    TacticalCase("capture-rook", "material-capture", "6k1/8/8/8/8/8/2r5/2RK4 w - - 0 1", ("c1c2",)),
    TacticalCase("capture-bishop", "material-capture", "6k1/8/8/8/8/8/1b6/1QK5 w - - 0 1", ("b1b2",)),
    TacticalCase("capture-knight", "material-capture", "6k1/8/8/8/8/8/4n3/4QK2 w - - 0 1", ("e1e2",)),
    TacticalCase("capture-pawn", "material-capture", "6k1/8/8/8/3p4/2P5/8/6K1 w - - 0 1", ("c3d4",)),
    TacticalCase("capture-black-queen", "material-capture", "3qk3/8/8/8/8/8/8/3QK3 b - - 0 1", ("d8d1",)),
    TacticalCase("promote-a-file", "promotion", "7k/P7/8/8/8/8/6K1/8 w - - 0 1", ("a7a8q",)),
    TacticalCase("promote-h-file", "promotion", "k7/7P/8/8/8/8/6K1/8 w - - 0 1", ("h7h8q",)),
    TacticalCase("promote-black-a", "promotion", "8/6k1/8/8/8/8/p7/7K b - - 0 1", ("a2a1q",)),
    TacticalCase("promote-black-h", "promotion", "K7/8/8/8/8/8/6kp/8 b - - 0 1", ("h2h1q",)),
    TacticalCase("promote-capture", "promotion", "r6k/1P6/8/8/8/8/6K1/8 w - - 0 1", ("b7a8q",)),
    TacticalCase("promote-black-capture", "promotion", "K7/8/8/8/8/7k/2p5/1R6 b - - 0 1", ("c2b1q",)),
    TacticalCase("evade-rook-file", "check-evasion", "4r1k1/8/8/8/8/8/8/4K3 w - - 0 1", ("e1f1",)),
    TacticalCase("evade-rook-rank", "check-evasion", "7k/8/8/8/8/8/1r6/1K6 w - - 0 1", ("b1a1",)),
    TacticalCase("evade-bishop", "check-evasion", "7k/8/8/8/8/8/1b6/2K5 w - - 0 1", ("c1d1",)),
    TacticalCase("evade-queen-diagonal", "check-evasion", "7k/8/8/8/8/8/3q4/2K5 w - - 0 1", ("c1b1",)),
    TacticalCase("evade-black-rook", "check-evasion", "4r1k1/8/8/8/8/8/8/4K3 b - - 0 1", ("e8d8",)),
    TacticalCase("evade-capture-checker", "check-evasion", "7k/8/8/8/8/8/2r5/2K5 w - - 0 1", ("c1c2",)),
    TacticalCase("fork-knight", "fork-or-skewer", "3q1rk1/8/4N3/8/8/8/8/4K3 w - - 0 1", ("e6f8",)),
    TacticalCase("fork-knight-queen", "fork-or-skewer", "6k1/3q4/8/2N5/8/8/8/4K3 w - - 0 1", ("c5d7",)),
    TacticalCase("fork-pawn", "fork-or-skewer", "6k1/3q1r2/4P3/8/8/8/8/4K3 w - - 0 1", ("e6e7",)),
    TacticalCase("skewer-rook", "fork-or-skewer", "4r1k1/8/8/8/8/8/4R3/6K1 w - - 0 1", ("e2e8",)),
    TacticalCase("skewer-bishop", "fork-or-skewer", "5rk1/8/8/8/2B5/8/8/6K1 w - - 0 1", ("c4f7",)),
    TacticalCase("fork-queen", "fork-or-skewer", "3q2k1/8/8/8/3N4/8/8/6K1 w - - 0 1", ("d4f5",)),
    TacticalCase("hanging-pawn", "hanging-piece", "6k1/8/8/8/4p3/3P4/8/6K1 w - - 0 1", ("d3e4",)),
    TacticalCase("hanging-bishop", "hanging-piece", "6k1/8/8/8/8/8/1b6/1Q4K1 w - - 0 1", ("b1b2",)),
    TacticalCase("hanging-rook", "hanging-piece", "6k1/8/8/8/8/8/1r6/1R4K1 w - - 0 1", ("b1b2",)),
    TacticalCase("hanging-queen", "hanging-piece", "6k1/8/8/8/8/8/3q4/3R2K1 w - - 0 1", ("d1d2",)),
    TacticalCase("hanging-black-rook", "hanging-piece", "k7/8/8/8/8/8/2p5/1R5K b - - 0 1", ("c2b1q",)),
    TacticalCase("hanging-black-pawn", "hanging-piece", "k7/8/8/8/8/2p5/3P4/7K b - - 0 1", ("c3d2",)),
)


def tactical_cases() -> tuple[TacticalCase, ...]:
    return _CASES


def _verified_target(environment: ChessEnvironment, move: str) -> float:
    before_turn = environment.turn
    environment.apply_uci(move)
    if environment.status().kind == "checkmate":
        return 1.0
    evaluator = RewardEvaluator()
    return float(max(-1.0, min(1.0, evaluator.evaluate_position(environment.board, before_turn, 0).potential)))


def generate_tactical_examples(seed: int, model_version: str, repetition: int = 1) -> list[ReplayExample]:
    if repetition < 1:
        raise ValueError("repetition must be positive")
    ordered = list(_CASES) * repetition
    random.Random(seed).shuffle(ordered)
    examples: list[ReplayExample] = []
    for index, case in enumerate(ordered):
        environment = ChessEnvironment.from_fen(case.fen)
        legal = set(environment.legal_moves())
        if not legal:
            raise ValueError(f"tactical case has no legal moves: {case.name}")
        if any(move not in legal for move in case.expected_moves):
            raise ValueError(f"invalid expected move in tactical case: {case.name}")
        target = _verified_target(ChessEnvironment.from_fen(case.fen), case.expected_moves[0])
        examples.append(
            ReplayExample(
                encode_board(environment.board),
                {move: 1.0 / len(case.expected_moves) for move in case.expected_moves},
                target,
                position=case.fen,
                seed=seed,
                game_index=index,
                model_version=model_version,
                source="tactical-curriculum",
                target_kind="tactical",
                self_play_config={"seed": seed, "repetition": repetition, "category": case.category},
                reward_components={"verified_target": target},
            )
        )
    return examples
