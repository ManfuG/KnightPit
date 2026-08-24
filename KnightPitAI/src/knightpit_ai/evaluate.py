from __future__ import annotations

import random
from typing import Any

from .board import ChessEnvironment
from .curriculum import TacticalCase, tactical_cases
from .mcts import MCTS, choose_move
from .model import PolicyValueNetwork
from .reward import RewardEvaluator
from .self_play import SelfPlayConfig, generate_self_play


def _tactical_success(case: TacticalCase, environment: ChessEnvironment, move: str) -> tuple[bool, str | None]:
    legal_moves = set(environment.legal_moves())
    if move not in legal_moves:
        return False, "illegal-move"
    try:
        move_object = next(item for item in environment.board.legal_moves() if item.uci() == move)
        destination = environment.board.squares[move_object.to_square]
        mover = environment.turn
        environment.apply_uci(move)
    except (StopIteration, ValueError):
        return False, "move-application-failed"
    status = environment.status().kind
    if case.category == "mate-in-one":
        return (status == "checkmate", None if status == "checkmate" else "not-checkmate")
    if move not in case.expected_moves:
        return False, "unexpected-move"
    if case.category == "promotion":
        piece = environment.board.squares[move_object.to_square]
        promoted = len(move) == 5 and piece is not None and piece.color == mover
        return (promoted, None if promoted else "not-promotion")
    if case.category in {"material-capture", "hanging-piece"}:
        captured = destination is not None and destination.color != mover
        success = captured or move_object.is_en_passant
        return (success, None if success else "no-capture")
    if case.category == "check-evasion":
        success = not environment.board.is_check()
        return (success, None if success else "still-in-check")
    return True, None


def evaluate_tactical_suite(
    network: PolicyValueNetwork,
    simulations: int = 4,
    seed: int = 42,
    tactical_plies: int = 0,
) -> dict[str, Any]:
    categories: dict[str, dict[str, Any]] = {}
    cases = tactical_cases()
    for index, case in enumerate(cases):
        environment = ChessEnvironment.from_fen(case.fen)
        tree = MCTS(network, simulations=simulations, tactical_plies=tactical_plies)
        counts = tree.search(environment.board, add_dirichlet_noise=False, rng=random.Random(seed + index))
        chosen = choose_move(counts, temperature=0.0, rng=random.Random(seed + index)) if counts else None
        legal = chosen in set(environment.legal_moves()) if chosen is not None else False
        success, reason = _tactical_success(case, environment, chosen) if chosen is not None else (False, "no-move")
        record = categories.setdefault(case.category, {"attempts": 0, "successes": 0, "cases": []})
        record["attempts"] += 1
        record["successes"] += int(success)
        record["cases"].append({
            "name": case.name,
            "chosen_move": chosen,
            "expected_moves": list(case.expected_moves),
            "legal": legal,
            "success": success,
            "failure_reason": reason,
            "search_stats": {
                "requested_simulations": tree.last_search_stats.requested_simulations,
                "completed_simulations": tree.last_search_stats.completed_simulations,
                "timed_out": tree.last_search_stats.timed_out,
                "tactical_extensions": tree.last_search_stats.tactical_extensions,
            },
        })
    total_attempts = 0
    total_successes = 0
    for record in categories.values():
        record["rate"] = record["successes"] / record["attempts"] if record["attempts"] else 0.0
        total_attempts += record["attempts"]
        total_successes += record["successes"]
    return {
        "model_version": network.version,
        "seed": seed,
        "simulations": simulations,
        "tactical_plies": tactical_plies,
        "attempts": total_attempts,
        "successes": total_successes,
        "rate": total_successes / total_attempts if total_attempts else 0.0,
        "categories": categories,
    }


def evaluate_match(
    candidate: PolicyValueNetwork,
    opponent: PolicyValueNetwork,
    games: int = 20,
    simulations: int = 8,
    max_ply: int = 120,
    seed: int = 42,
    time_limit_seconds: float | None = None,
    tactical_plies: int = 0,
) -> dict[str, Any]:
    if games < 1:
        raise ValueError("evaluation requires at least one game")
    candidate_wins = candidate_losses = draws = 0
    legal_moves = move_attempts = total_plies = 0
    terminal_games = max_ply_games = 0
    checkmate_wins = checkmate_losses = captures = white_captures = black_captures = 0
    material_delta_sum = opening_center_sum = opening_development_sum = 0.0
    opening_positions = 0
    completed_simulations = requested_simulations = tactical_extensions = timed_out_searches = 0
    reasons: dict[str, int] = {}
    evaluator = RewardEvaluator()
    for game_index in range(games):
        candidate_white = game_index % 2 == 0
        candidate_network = candidate if candidate_white else opponent
        opponent_network = opponent if candidate_white else candidate
        tree_kwargs: dict[str, Any] = {"simulations": simulations, "tactical_plies": tactical_plies}
        if time_limit_seconds is not None:
            tree_kwargs["time_limit_seconds"] = time_limit_seconds
        candidate_tree = MCTS(candidate_network, **tree_kwargs)
        opponent_tree = MCTS(opponent_network, **tree_kwargs)
        rng = random.Random(seed + game_index)
        environment = ChessEnvironment.initial()
        for ply in range(max_ply):
            if environment.is_terminal():
                break
            board = environment.board
            tree = candidate_tree if (environment.turn == "white") == candidate_white else opponent_tree
            counts = tree.search(board, add_dirichlet_noise=False, rng=rng, ply=ply)
            stats = tree.last_search_stats
            requested_simulations += stats.requested_simulations
            completed_simulations += stats.completed_simulations
            tactical_extensions += stats.tactical_extensions
            timed_out_searches += int(stats.timed_out)
            if not counts:
                break
            move = choose_move(counts, temperature=0.0, rng=rng)
            legal = move in environment.legal_moves()
            move_attempts += 1
            legal_moves += int(legal)
            if not legal:
                break
            move_object = next(legal_move for legal_move in board.legal_moves() if legal_move.uci() == move)
            before = board
            before_eval = evaluator.evaluate_position(before, before.turn, ply)
            environment.apply_uci(move)
            transition = evaluator.evaluate_transition(before, environment.board, move_object, before.turn, ply)
            if transition.captured_value > 0.0:
                captures += 1
                if before.turn == "white":
                    white_captures += 1
                else:
                    black_captures += 1
            white_transition = evaluator.evaluate_transition(before, environment.board, move_object, "white", ply)
            material_delta_sum += white_transition.material_delta
            if ply < evaluator.profile.opening_plies:
                opening_positions += 1
                opening_center_sum += before_eval.center
                opening_development_sum += before_eval.development
            candidate_tree.advance(move)
            opponent_tree.advance(move)
            total_plies += 1
        if environment.is_terminal():
            terminal_games += 1
            is_checkmate = environment.status().kind == "checkmate"
            reason = "checkmate" if is_checkmate else "regulatory-draw"
        else:
            max_ply_games += 1
            is_checkmate = False
            reason = "max-ply"
        reasons[reason] = reasons.get(reason, 0) + 1
        result = environment.result_white_perspective() if environment.is_terminal() else 0.0
        candidate_result = result if candidate_white else -result
        if candidate_result > 0:
            candidate_wins += 1
            if is_checkmate:
                checkmate_wins += 1
        elif candidate_result < 0:
            candidate_losses += 1
            if is_checkmate:
                checkmate_losses += 1
        else:
            draws += 1
    score = (candidate_wins + 0.5 * draws) / games
    return {
        "candidate_version": candidate.version,
        "opponent_version": opponent.version,
        "games": games,
        "wins": candidate_wins,
        "losses": candidate_losses,
        "draws": draws,
        "score": score,
        "legal_move_rate": legal_moves / move_attempts if move_attempts else 1.0,
        "terminal_games": terminal_games,
        "max_ply_games": max_ply_games,
        "average_ply": total_plies / games,
        "termination_reasons": reasons,
        "checkmate_wins": checkmate_wins,
        "checkmate_losses": checkmate_losses,
        "checkmate_rate": (checkmate_wins + checkmate_losses) / games,
        "captures": captures,
        "white_captures": white_captures,
        "black_captures": black_captures,
        "material_delta_average": material_delta_sum / total_plies if total_plies else 0.0,
        "opening_center_average": opening_center_sum / opening_positions if opening_positions else 0.0,
        "opening_development_average": opening_development_sum / opening_positions if opening_positions else 0.0,
        "colors_alternated": True,
        "seed": seed,
        "tactical_plies": tactical_plies,
        "requested_simulations": requested_simulations,
        "completed_simulations": completed_simulations,
        "timed_out_searches": timed_out_searches,
        "tactical_extensions": tactical_extensions,
    }


def evaluate_network(
    network: PolicyValueNetwork,
    games: int = 20,
    simulations: int = 8,
    max_ply: int = 120,
    seed: int = 42,
) -> dict[str, Any]:
    _, stats = generate_self_play(
        network,
        SelfPlayConfig(
            games=games,
            simulations=simulations,
            max_ply=max_ply,
            temperature=0.0,
            temperature_cutoff=0,
            seed=seed,
            evaluation=True,
            root_noise=False,
            tactical_plies=0,
        ),
    )
    losses = getattr(network, "last_metrics", {})
    score = (stats.white_wins + 0.5 * stats.draws) / stats.games if stats.games else 0.0
    return {
        "model_version": network.version,
        "games": stats.games,
        "completed_games": stats.completed,
        "legal_move_rate": stats.legal_move_rate,
        "average_ply": stats.average_ply,
        "white_wins": stats.white_wins,
        "black_wins": stats.black_wins,
        "draws": stats.draws,
        "score": score,
        "terminal_games": stats.terminal_games,
        "max_ply_games": stats.max_ply_games,
        "termination_reasons": stats.termination_reasons,
        "checkmate_wins": stats.checkmate_wins,
        "checkmate_losses": stats.checkmate_losses,
        "checkmate_rate": stats.checkmate_games / stats.games if stats.games else 0.0,
        "captures": stats.captures,
        "white_captures": stats.white_captures,
        "black_captures": stats.black_captures,
        "material_delta_average": stats.material_delta_average,
        "opening_center_average": stats.opening_center_average,
        "opening_development_average": stats.opening_development_average,
        "policy_loss": losses.get("policy_loss"),
        "value_loss": losses.get("value_loss"),
        "tactical_suite": evaluate_tactical_suite(network, simulations=max(1, min(simulations, 4)), seed=seed, tactical_plies=0),
        "note": "Losses are the latest persisted training metrics; evaluation measures legal self-play behavior and the real tactical suite.",
    }
