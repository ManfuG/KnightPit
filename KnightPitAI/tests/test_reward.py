import json

from knightpit_ai.board import ChessEnvironment
from knightpit_ai.campaign import promotion_gates
from knightpit_ai.mcts import MCTS
from knightpit_ai.model import PolicyValueNetwork
from knightpit_ai.replay_buffer import ReplayBuffer
from knightpit_ai.reward import RewardEvaluator, RewardProfile
from knightpit_ai.self_play import SelfPlayConfig, generate_self_play


def test_initial_and_opening_principles_are_bounded():
    evaluator = RewardEvaluator()
    environment = ChessEnvironment.initial()
    initial = evaluator.evaluate_position(environment.board, "white", 0)
    assert initial == type(initial)(0.0, 0.0, 0.0, 0.0)
    environment.apply_uci("e2e4")
    assert evaluator.evaluate_position(environment.board, "white", 1).center > 0.0
    environment.apply_uci("a7a6")
    environment.apply_uci("g1f3")
    assert evaluator.evaluate_position(environment.board, "white", 3).development > 0.0
    environment.apply_uci("b7b6")
    environment.apply_uci("f1c4")
    assert evaluator.evaluate_position(environment.board, "white", 5).development > 0.0
    assert evaluator.evaluate_position(environment.board, "white", 21).development == 0.0


def test_capture_terminal_and_perspective_signs():
    evaluator = RewardEvaluator()
    environment = ChessEnvironment.from_fen("6k1/8/8/8/8/8/3q4/3QK3 w - - 0 1")
    before = environment.board
    move = next(move for move in before.legal_moves() if move.uci() == "d1d2")
    environment.apply_uci("d1d2")
    transition = evaluator.evaluate_transition(before, environment.board, move, "white", 0)
    assert transition.captured_value == 9.0
    assert transition.material_delta > 0.0
    assert evaluator.evaluate_position(before, "black", 0).material == 0.0

    mate = ChessEnvironment.from_fen("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
    mate.apply_uci("f7g7")
    assert evaluator.terminal_target(mate, "white") == 1.0
    assert evaluator.terminal_target(mate, "black") == -1.0

    en_passant = ChessEnvironment.from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    before = en_passant.board
    move = next(move for move in before.legal_moves() if move.uci() == "e5d6")
    en_passant.apply_uci("e5d6")
    transition = evaluator.evaluate_transition(before, en_passant.board, move, "white", 0)
    assert transition.captured_value == 1.0
    assert transition.material_delta > 0.0


def test_schedule_scales_center_development_and_heuristic():
    first = RewardProfile.for_iteration(1)
    middle = RewardProfile.for_iteration(6)
    final = RewardProfile.for_iteration(12)
    assert abs(middle.center_weight - 0.30 * 6 / 11) < 1e-12
    assert final.center_weight == 0.0
    assert first.development_weight == 0.15
    assert middle.development_weight == 0.075
    assert final.development_weight == 0.0
    assert first.mcts_heuristic_weight == 0.20
    assert middle.mcts_heuristic_weight == 0.10
    assert final.mcts_heuristic_weight == 0.0


def test_replay_preserves_reward_components_and_legacy_profile(tmp_path):
    path = tmp_path / "replay.jsonl"
    replay, stats = generate_self_play(
        PolicyValueNetwork(seed=7),
        SelfPlayConfig(games=1, simulations=1, max_ply=4, seed=7),
        path,
    )
    loaded = ReplayBuffer.load_jsonl(path)
    assert loaded._items[0].reward_components == replay._items[0].reward_components
    assert stats.legal_move_rate == 1.0
    legacy = tmp_path / "legacy.jsonl"
    record = replay._items[0].to_record()
    record.pop("reward_components")
    legacy.write_text(json.dumps(record) + "\n", encoding="utf-8")
    old = ReplayBuffer.load_jsonl(legacy)
    assert old._items[0].reward_components == {}
    assert old._items[0].self_play_config["reward_profile"] == "legacy-material"


def test_schedule_and_mcts_blend_are_deterministic():
    assert RewardProfile.for_iteration(1) == RewardProfile.for_iteration(1)
    assert RewardProfile.for_iteration(1).mcts_heuristic_weight == 0.20
    assert RewardProfile.for_iteration(5).mcts_heuristic_weight == 0.10
    assert RewardProfile.for_iteration(9).mcts_heuristic_weight == 0.0
    board = ChessEnvironment.initial().board
    first = MCTS(PolicyValueNetwork(seed=3), simulations=2).search(board)
    second = MCTS(PolicyValueNetwork(seed=3), simulations=2).search(board)
    assert first == second


def test_promotion_gates_cover_score_and_regressions():
    champion = {"games": 20, "legal_move_rate": 1.0, "score": 0.55, "checkmate_losses": 2, "material_delta_average": 0.0}
    assert not promotion_gates({**champion, "games": 4}, champion)
    assert not promotion_gates({**champion, "score": 0.50}, champion)
    assert not promotion_gates({**champion, "material_delta_average": -0.11}, champion)
    assert promotion_gates(champion, champion)
