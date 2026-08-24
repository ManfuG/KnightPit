from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from .board import BoardState, ChessEnvironment, Color, Move
from .encoding import encode_board
from .mcts import MCTS, choose_move
from .model import PolicyValueNetwork
from .replay_buffer import ReplayBuffer, ReplayExample
from .reward import RewardEvaluator, RewardProfile, TransitionEvaluation


@dataclass(frozen=True)
class SelfPlayConfig:
    games: int = 8
    simulations: int = 16
    max_ply: int = 240
    temperature: float = 1.0
    temperature_cutoff: int = 30
    seed: int = 42
    replay_capacity: int = 10_000
    iteration: int = 1
    model_version: str = "untrained"
    evaluation: bool = False
    root_noise: bool = True
    time_limit_seconds: float | None = None
    reward_profile: str = "principles-v1"
    tactical_plies: int = 0


@dataclass(frozen=True)
class GameTrace:
    examples: list[ReplayExample]
    plies: int
    termination: str
    result: float
    captures: int = 0
    white_captures: int = 0
    black_captures: int = 0
    material_delta_sum: float = 0.0
    opening_center_sum: float = 0.0
    opening_development_sum: float = 0.0
    opening_positions: int = 0


@dataclass(frozen=True)
class SelfPlayStats:
    games: int
    completed: int
    plies: int
    white_wins: int
    black_wins: int
    draws: int
    legal_moves: int
    move_attempts: int
    terminal_games: int = 0
    max_ply_games: int = 0
    checkmate_games: int = 0
    regulatory_draw_games: int = 0
    termination_reasons: dict[str, int] = field(default_factory=dict)
    effective_seeds: tuple[int, ...] = ()
    captures: int = 0
    white_captures: int = 0
    black_captures: int = 0
    material_delta_sum: float = 0.0
    opening_center_average: float = 0.0
    opening_development_average: float = 0.0
    opening_positions: int = 0
    checkmate_wins: int = 0
    checkmate_losses: int = 0

    @property
    def legal_move_rate(self) -> float:
        return self.legal_moves / self.move_attempts if self.move_attempts else 1.0

    @property
    def average_ply(self) -> float:
        return self.plies / self.games if self.games else 0.0

    @property
    def material_delta_average(self) -> float:
        return self.material_delta_sum / self.plies if self.plies else 0.0


def _termination(environment: ChessEnvironment, reached_max_ply: bool) -> tuple[str, float]:
    if reached_max_ply and not environment.is_terminal():
        return "max-ply", 0.0
    status = environment.status()
    if status.kind == "checkmate":
        return "checkmate", environment.result_white_perspective()
    return "regulatory-draw", environment.result_white_perspective()


def _profile_for(config: SelfPlayConfig) -> RewardProfile:
    if config.reward_profile != "principles-v1":
        raise ValueError(f"unsupported reward profile: {config.reward_profile}")
    return RewardProfile.for_iteration(config.iteration)


def play_game(
    network: PolicyValueNetwork,
    config: SelfPlayConfig,
    game_seed: int,
    game_index: int = 0,
) -> GameTrace:
    rng = random.Random(game_seed)
    profile = _profile_for(config)
    evaluator = RewardEvaluator(profile)
    heuristic_weight = 0.0 if config.evaluation else profile.mcts_heuristic_weight
    tree = MCTS(
        network,
        simulations=config.simulations,
        time_limit_seconds=config.time_limit_seconds,
        evaluator=evaluator if heuristic_weight else None,
        heuristic_weight=heuristic_weight,
        tactical_plies=config.tactical_plies,
    )
    environment = ChessEnvironment.initial()
    positions: list[tuple[str, np.ndarray, dict[str, float], Color, BoardState, Move, TransitionEvaluation]] = []
    for ply in range(config.max_ply):
        if environment.is_terminal():
            break
        board = environment.board
        counts = tree.search(
            board,
            add_dirichlet_noise=config.root_noise and not config.evaluation,
            rng=rng,
            ply=ply,
        )
        if not counts:
            break
        temperature = 0.0 if config.evaluation else (config.temperature if ply < config.temperature_cutoff else 0.0)
        move = choose_move(counts, temperature, rng)
        move_object = next(legal for legal in board.legal_moves() if legal.uci() == move)
        fen = board.fen()
        features = encode_board(board)
        policy = {key: value / max(1, sum(counts.values())) for key, value in counts.items()}
        turn = board.turn
        environment.apply_uci(move)
        after = environment.board
        transition = evaluator.evaluate_transition(board, after, move_object, turn, ply)
        positions.append((fen, features, policy, turn, board, move_object, transition))
        tree.advance(move)
        if not config.evaluation and ((ply + 1) % 8 == 0 or ply + 1 == config.max_ply):
            print(
                f"[self-train] game_index={game_index} ply={ply + 1}/{config.max_ply} "
                f"seed={game_seed} simulations={config.simulations} tactical_plies={config.tactical_plies}",
                flush=True,
            )
    termination, result = _termination(environment, len(positions) >= config.max_ply)
    config_data = asdict(config)
    config_data["age_group"] = "recent"
    examples: list[ReplayExample] = []
    captures = white_captures = black_captures = 0
    material_delta_sum = opening_center_sum = opening_development_sum = 0.0
    opening_positions = 0
    for ply, (fen, features, policy, turn, position_board, move, transition) in enumerate(positions):
        if termination == "max-ply":
            target = evaluator.evaluate_position(position_board, turn, ply).potential
            target_kind = "max-ply-potential"
        else:
            target = evaluator.terminal_target(environment, turn)
            target_kind = "terminal"
        before = transition.before
        captured = transition.captured_value
        captures += int(captured > 0.0)
        if captured > 0.0:
            if turn == "white":
                white_captures += 1
            else:
                black_captures += 1
        white_transition = evaluator.evaluate_transition(position_board, position_board.push(move), move, "white", ply)
        material_delta_sum += white_transition.material_delta
        if ply < profile.opening_plies:
            opening_positions += 1
            opening_center_sum += before.center if turn == "white" else -before.center
            opening_development_sum += before.development if turn == "white" else -before.development
        components = {
            "material": before.material,
            "center": before.center,
            "development": before.development,
            "potential": before.potential,
            "material_delta": transition.material_delta,
            "captured_value": transition.captured_value,
            "target": float(target),
        }
        examples.append(
            ReplayExample(
                features,
                policy,
                float(max(-1.0, min(1.0, target))),
                position=fen,
                seed=game_seed,
                game_index=game_index,
                model_version=network.version,
                source="self-play",
                target_kind=target_kind,
                self_play_config=config_data,
                reward_components=components,
            )
        )
    return GameTrace(
        examples,
        len(positions),
        termination,
        result,
        captures,
        white_captures,
        black_captures,
        material_delta_sum,
        opening_center_sum,
        opening_development_sum,
        opening_positions,
    )


def generate_self_play(
    network: PolicyValueNetwork,
    config: SelfPlayConfig,
    output: str | Path | None = None,
    replay: ReplayBuffer | None = None,
    progress_callback: Callable[[int, int, GameTrace], None] | None = None,
) -> tuple[ReplayBuffer, SelfPlayStats]:
    replay = replay if replay is not None else ReplayBuffer(config.replay_capacity)
    completed = total_plies = 0
    white_wins = black_wins = draws = 0
    legal_moves = move_attempts = 0
    terminal_games = max_ply_games = checkmate_games = regulatory_draw_games = 0
    reasons: dict[str, int] = {}
    seeds: list[int] = []
    captures = white_captures = black_captures = 0
    material_delta_sum = opening_center_sum = opening_development_sum = 0.0
    opening_positions = checkmate_wins = checkmate_losses = 0
    for game_index in range(config.games):
        game_seed = config.seed + game_index
        seeds.append(game_seed)
        trace = play_game(network, config, game_seed, game_index)
        if progress_callback is not None:
            progress_callback(game_index + 1, config.games, trace)
        replay.extend(trace.examples)
        total_plies += trace.plies
        move_attempts += trace.plies
        legal_moves += trace.plies
        completed += 1
        reasons[trace.termination] = reasons.get(trace.termination, 0) + 1
        captures += trace.captures
        white_captures += trace.white_captures
        black_captures += trace.black_captures
        material_delta_sum += trace.material_delta_sum
        opening_center_sum += trace.opening_center_sum
        opening_development_sum += trace.opening_development_sum
        opening_positions += trace.opening_positions
        if trace.termination == "max-ply":
            max_ply_games += 1
        else:
            terminal_games += 1
            if trace.termination == "checkmate":
                checkmate_games += 1
                if trace.result > 0:
                    checkmate_wins += 1
                elif trace.result < 0:
                    checkmate_losses += 1
            else:
                regulatory_draw_games += 1
        if trace.result > 0:
            white_wins += 1
        elif trace.result < 0:
            black_wins += 1
        else:
            draws += 1
    stats = SelfPlayStats(
        games=config.games,
        completed=completed,
        plies=total_plies,
        white_wins=white_wins,
        black_wins=black_wins,
        draws=draws,
        legal_moves=legal_moves,
        move_attempts=move_attempts,
        terminal_games=terminal_games,
        max_ply_games=max_ply_games,
        checkmate_games=checkmate_games,
        regulatory_draw_games=regulatory_draw_games,
        termination_reasons=reasons,
        effective_seeds=tuple(seeds),
        captures=captures,
        white_captures=white_captures,
        black_captures=black_captures,
        material_delta_sum=material_delta_sum,
        opening_center_average=opening_center_sum / opening_positions if opening_positions else 0.0,
        opening_development_average=opening_development_sum / opening_positions if opening_positions else 0.0,
        opening_positions=opening_positions,
        checkmate_wins=checkmate_wins,
        checkmate_losses=checkmate_losses,
    )
    if output is not None:
        destination = replay.save_jsonl(output)
        manifest = destination.with_suffix(destination.suffix + ".manifest.json")
        manifest.write_text(
            json.dumps({"config": asdict(config), "stats": asdict(stats), "model_version": network.version}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return replay, stats
