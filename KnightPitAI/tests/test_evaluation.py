import json
import random
from pathlib import Path
import numpy as np

from knightpit_ai.board import ChessEnvironment, parse_square

from knightpit_ai.encoding import MOVE_SPACE_SIZE, move_to_index
from knightpit_ai.mcts import MCTS, choose_move
from knightpit_ai.model import PolicyValueNetwork, Prediction


class TacticalNetwork(PolicyValueNetwork):
    def __init__(self, expected_move: str) -> None:
        super().__init__(seed=19)
        self.expected_move = expected_move

    def predict(self, board):
        logits = np.zeros(MOVE_SPACE_SIZE, dtype=np.float32)
        for move in board.legal_moves():
            logits[move_to_index(move)] = 100.0 if move.uci() == self.expected_move else 0.0
        return Prediction(logits=logits, value=0.0)


def test_tactical_suite_inference_selects_expected_moves():
    fixtures = json.loads((Path(__file__).parent / "fixtures" / "tactics.json").read_text(encoding="utf-8"))
    for fixture in fixtures:
        environment = ChessEnvironment.from_fen(fixture["fen"])
        counts = MCTS(TacticalNetwork(fixture["expected_move"]), simulations=2).search(environment.board)
        move = choose_move(counts, temperature=0.0, rng=random.Random(0))
        assert move == fixture["expected_move"], fixture["name"]
        environment.apply_uci(move)
        if fixture["name"] == "mate-in-one":
            assert environment.status().kind == "checkmate"
        elif fixture["name"] == "material-capture":
            captured = environment.board.piece_at(parse_square("d2"))
            assert captured is not None and captured.color == "white" and captured.kind == "queen"
        else:
            promoted = environment.board.piece_at(0)
            assert promoted is not None and promoted.kind == "queen"
