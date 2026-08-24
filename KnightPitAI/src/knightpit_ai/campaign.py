from __future__ import annotations

import copy
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .curriculum import generate_tactical_examples
from .evaluate import evaluate_match, evaluate_tactical_suite
from .model import PolicyValueNetwork
from .replay_buffer import ReplayBuffer
from .reward import RewardProfile
from .self_play import GameTrace, SelfPlayConfig, SelfPlayStats, generate_self_play
from .train import TrainingConfig, train_network


@dataclass(frozen=True)
class CampaignConfig:
    minutes: float | None
    seed: int
    simulations: int
    max_ply: int
    games_per_iteration: int
    replay_capacity: int
    train_epochs: int
    batch_size: int
    eval_games: int
    checkpoint_every_iteration: bool
    resume: bool
    output_dir: str | Path
    learning_rate: float = 0.01
    reward_profile: str = "principles-v1"
    initial_checkpoint: str | Path | None = None
    total_self_play_games: int | None = None
    no_time_limit: bool = False
    continue_candidate: bool = False
    tactical_plies: int = 0
    max_examples_per_epoch: int | None = None
    recent_fraction: float = 0.60
    tactical_fraction: float = 0.20
    campaign_id: str | None = None
    command: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_metadata(path: Path) -> dict[str, Any] | None:
    try:
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            return json.loads(str(data["metadata"]))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _manifest(config: CampaignConfig, resumed: bool, fallback: bool) -> dict[str, Any]:
    payload = asdict(config)
    payload["output_dir"] = str(config.output_dir)
    payload["initial_checkpoint"] = str(config.initial_checkpoint) if config.initial_checkpoint is not None else None
    profile = RewardProfile.for_iteration(1)
    baseline = Path(config.initial_checkpoint) if config.initial_checkpoint is not None else None
    return {
        "campaign_version": "3",
        "campaign_id": config.campaign_id or f"campaign-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}",
        "command": config.command or " ".join(sys.argv),
        "started_at": _now(),
        "updated_at": _now(),
        "seed": config.seed,
        "config": payload,
        "reward_profile": config.reward_profile,
        "reward_schedule_version": profile.schedule_version,
        "reward_schedule": {
            "material_weight": profile.material_weight,
            "center_weight": profile.center_weight,
            "development_weight": profile.development_weight,
            "mcts_heuristic_weight": profile.mcts_heuristic_weight,
        },
        "cpu_mode": True,
        "cpu": platform.processor() or platform.machine(),
        "python": platform.python_version(),
        "code_version": "knightpit-ai-campaign-quality-v2",
        "license_policy": "Project code and generated data MIT; dependencies retain their licenses.",
        "data_policy": "Self-play and project-owned tactical curriculum only; no external engine, external dataset, tablebase, or cloud API.",
        "resumed": resumed,
        "resume_fallback": fallback,
        "initial_checkpoint": str(baseline) if baseline is not None else None,
        "initial_checkpoint_sha256": _sha256(baseline) if baseline is not None else None,
        "initial_checkpoint_metadata": _checkpoint_metadata(baseline) if baseline is not None else None,
        "initial_checkpoint_fallback": False,
        "architecture": None,
        "total_self_play_games": config.total_self_play_games,
        "no_time_limit": config.no_time_limit,
        "continue_candidate": config.continue_candidate,
        "completed_self_play_games": 0,
        "replay_policy": "new-run starts empty; legacy replay is never implicitly imported",
        "replay_sources": {},
        "phase": "initializing",
        "completed_phase": None,
        "status": "running",
        "termination_reason": None,
        "iterations": [],
    }


def _remaining(deadline: float | None) -> float:
    if deadline is None:
        return float("inf")
    return max(0.0, deadline - time.monotonic())


def _rate(metrics: dict[str, Any], field: str) -> float:
    games = int(metrics.get("games", 0) or 0)
    return float(metrics.get(field, 0.0)) / games if games else 0.0


def promotion_gates(candidate: dict[str, Any], champion: dict[str, Any]) -> bool:
    """Apply match and tactical anti-regression promotion gates."""
    if int(candidate.get("games", 0)) < 20:
        return False
    if not (
        candidate.get("legal_move_rate") == 1.0
        and float(candidate.get("score", 0.0)) >= 0.55
        and _rate(candidate, "checkmate_losses") <= _rate(champion, "checkmate_losses") + 0.05
        and float(candidate.get("material_delta_average", 0.0)) >= float(champion.get("material_delta_average", 0.0)) - 0.10
    ):
        return False
    candidate_suite = candidate.get("tactical_suite", {}).get("categories", {})
    champion_suite = champion.get("tactical_suite", {}).get("categories", {})
    critical = {"mate-in-one", "promotion", "check-evasion"}
    for category, baseline in champion_suite.items():
        candidate_rate = float(candidate_suite.get(category, {}).get("rate", 0.0))
        baseline_rate = float(baseline.get("rate", 0.0))
        allowance = 0.0 if category in critical else 0.10
        if candidate_rate < baseline_rate - allowance:
            return False
    return True


def _source_counts(replay: ReplayBuffer) -> dict[str, int]:
    return dict(Counter(item.source for item in replay._items))


def run_campaign(config: CampaignConfig) -> dict[str, Any]:
    if config.no_time_limit and (config.total_self_play_games is None or config.total_self_play_games < 1):
        raise ValueError("unlimited campaigns require total_self_play_games")
    if not config.no_time_limit and (config.minutes is None or config.minutes <= 0):
        raise ValueError("minutes must be greater than zero")
    if config.total_self_play_games is not None and config.total_self_play_games < 1:
        raise ValueError("total_self_play_games must be positive")
    if config.reward_profile != "principles-v1":
        raise ValueError(f"unsupported reward profile: {config.reward_profile}")
    if config.tactical_plies < 0:
        raise ValueError("tactical_plies must be non-negative")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "campaign_manifest.json"
    replay_path = output_dir / "replay.jsonl"
    metrics_path = output_dir / "campaign_metrics.jsonl"
    champion_path = output_dir / "champion.npz"
    resumed = bool(config.resume)
    previous = _load_manifest(manifest_path) if resumed else None
    if previous is not None and previous.get("reward_profile", config.reward_profile) != config.reward_profile:
        raise ValueError("resume reward profile mismatch")
    fallback = False
    replay = ReplayBuffer(config.replay_capacity)
    if resumed:
        replay = ReplayBuffer.load_jsonl(replay_path, config.replay_capacity)
    manifest = previous if previous is not None else _manifest(config, resumed, False)
    effective_config = asdict(config)
    effective_config["output_dir"] = str(config.output_dir)
    effective_config["initial_checkpoint"] = str(config.initial_checkpoint) if config.initial_checkpoint is not None else None
    if previous is not None and manifest.get("config") != effective_config:
        manifest.setdefault("config_history", []).append(manifest.get("config"))
    manifest["config"] = effective_config
    manifest["updated_at"] = _now()
    manifest["status"] = "running"
    manifest["command"] = config.command or manifest.get("command") or " ".join(sys.argv)
    if previous is not None:
        manifest["resumed"] = True

    if resumed and champion_path.exists():
        try:
            champion = PolicyValueNetwork.load_checkpoint(
                champion_path,
                expected_reward_profile=config.reward_profile,
                expected_reward_schedule_version=RewardProfile.for_iteration(1).schedule_version,
            )
        except (OSError, ValueError, KeyError):
            champion = PolicyValueNetwork(seed=config.seed, hidden_size=64, policy_rank=16, learning_rate=config.learning_rate)
            fallback = True
    elif not resumed and config.initial_checkpoint is not None:
        try:
            champion = PolicyValueNetwork.load_checkpoint(
                config.initial_checkpoint,
                expected_reward_profile=config.reward_profile,
                expected_reward_schedule_version=RewardProfile.for_iteration(1).schedule_version,
            )
        except (OSError, ValueError, KeyError):
            champion = PolicyValueNetwork(seed=config.seed, hidden_size=64, policy_rank=16, learning_rate=config.learning_rate)
            fallback = True
            manifest["initial_checkpoint_fallback"] = True
    else:
        champion = PolicyValueNetwork(seed=config.seed, hidden_size=64, policy_rank=16, learning_rate=config.learning_rate)
        fallback = resumed
    manifest["resume_fallback"] = fallback
    manifest["architecture"] = {
        "input_size": champion.input_size,
        "hidden_size": champion.hidden_size,
        "policy_rank": champion.policy_rank,
    }
    manifest["baseline_checkpoint_sha256"] = _sha256(champion_path if resumed and champion_path.exists() else Path(config.initial_checkpoint) if config.initial_checkpoint else champion_path)
    champion.version = champion.version if champion.version != "untrained" else "champion-initial"

    def save_checkpoint(model: PolicyValueNetwork, path: Path, **kwargs: Any) -> None:
        model.save_checkpoint(
            path,
            seed=config.seed,
            replay_examples=len(replay),
            reward_profile=config.reward_profile,
            reward_schedule_version=RewardProfile.for_iteration(1).schedule_version,
            **kwargs,
        )

    if not champion_path.exists() or fallback or not resumed:
        save_checkpoint(champion, champion_path)
    manifest["phase"] = "baseline-evaluation" if previous is None and config.initial_checkpoint is not None and Path(config.initial_checkpoint).exists() and not fallback else "initializing"
    _write_json(manifest_path, manifest)
    if previous is None and config.initial_checkpoint is not None and Path(config.initial_checkpoint).exists() and not fallback:
        baseline_evaluation = evaluate_match(
            champion,
            champion,
            games=40,
            simulations=4,
            max_ply=config.max_ply,
            seed=config.seed,
            tactical_plies=0,
        )
        baseline_evaluation["tactical_suite"] = evaluate_tactical_suite(champion, simulations=4, seed=config.seed + 303, tactical_plies=0)
        manifest["baseline_evaluation"] = baseline_evaluation
        _write_json(manifest_path, manifest)
    start_iteration = len(manifest.get("iterations", [])) + 1
    active_iteration = int(manifest.get("active_iteration", start_iteration))
    resume_phase = manifest.get("phase") if resumed and active_iteration == start_iteration else None
    completed_self_play_games = int(manifest.get("completed_self_play_games", 0))
    target_self_play_games = config.total_self_play_games
    deadline = None if config.no_time_limit else time.monotonic() + float(config.minutes) * 60.0
    grace = config.minutes is not None and config.minutes < 1.0
    results: list[dict[str, Any]] = []
    interrupted = False
    training_base = champion
    latest_candidate_path: Path | None = None

    def deadline_expired() -> bool:
        return not config.no_time_limit and _remaining(deadline) <= 0 and not grace

    def phase_budget(fraction: float) -> float | None:
        if config.no_time_limit:
            return None
        return max(0.001, _remaining(deadline) * fraction)

    def move_time_budget(fraction: float, units: int) -> float | None:
        budget = phase_budget(fraction)
        if budget is None:
            return None
        return min(0.01, max(0.001, budget / max(1, units)))

    try:
        iteration = active_iteration
        while (target_self_play_games is None or completed_self_play_games < target_self_play_games) and _remaining(deadline) > 0:
            games_this_iteration = config.games_per_iteration
            if target_self_play_games is not None:
                games_this_iteration = min(games_this_iteration, target_self_play_games - completed_self_play_games)
            if games_this_iteration <= 0:
                break
            iteration_seed = config.seed + iteration * 1_000_003
            self_play_network = training_base if config.continue_candidate else champion
            manifest["active_iteration"] = iteration
            manifest["active_iteration_seed"] = iteration_seed
            manifest["phase"] = "self-play"
            _write_json(manifest_path, manifest)
            if resume_phase in {"self-play-complete", "training", "training-complete", "evaluation"} and manifest.get("active_self_play_stats"):
                self_play_stats = SelfPlayStats(**manifest["active_self_play_stats"])
                if resume_phase == "self-play-complete":
                    resume_phase = None
            else:
                def report_progress(completed: int, total: int, trace: GameTrace) -> None:
                    target_text = str(target_self_play_games) if target_self_play_games is not None else "unbounded"
                    print(f"[self-train] iteration={iteration} game={completed}/{total} total={completed_self_play_games + completed}/{target_text} plies={trace.plies} termination={trace.termination}", flush=True)

                self_play_config = SelfPlayConfig(
                    games=games_this_iteration,
                    simulations=config.simulations,
                    max_ply=config.max_ply,
                    temperature=1.0,
                    temperature_cutoff=min(20, config.max_ply),
                    seed=iteration_seed,
                    replay_capacity=config.replay_capacity,
                    iteration=iteration,
                    model_version=self_play_network.version,
                    root_noise=True,
                    time_limit_seconds=move_time_budget(0.5, games_this_iteration * config.max_ply),
                    reward_profile=config.reward_profile,
                    tactical_plies=config.tactical_plies,
                )
                replay, self_play_stats = generate_self_play(self_play_network, self_play_config, replay=replay, progress_callback=report_progress)
                completed_self_play_games += self_play_stats.games
                replay.extend(generate_tactical_examples(iteration_seed, self_play_network.version))
                replay.save_jsonl(replay_path)
                manifest["completed_self_play_games"] = completed_self_play_games
                manifest["active_self_play_stats"] = asdict(self_play_stats)
                manifest["replay_sources"] = _source_counts(replay)
                manifest["replay_sha256"] = _sha256(replay_path)
                manifest["phase"] = "self-play-complete"
                manifest["completed_phase"] = "self-play"
                _write_json(manifest_path, manifest)
            if deadline_expired():
                raise TimeoutError("deadline after self-play")

            candidate_path = output_dir / f"candidate-iteration-{iteration}.npz"
            latest_candidate_path = output_dir / "latest-candidate.npz"
            if resume_phase in {"training-complete", "evaluation"} and candidate_path.exists():
                candidate = PolicyValueNetwork.load_checkpoint(
                    candidate_path,
                    expected_reward_profile=config.reward_profile,
                    expected_reward_schedule_version=RewardProfile.for_iteration(1).schedule_version,
                )
                training_history = manifest.get("active_training_history", [])
                resume_phase = None
            else:
                manifest["phase"] = "training"
                _write_json(manifest_path, manifest)
                candidate = copy.deepcopy(self_play_network)
                candidate.version = f"candidate-iteration-{iteration}"
                training_history = train_network(
                    candidate,
                    replay,
                    TrainingConfig(
                        epochs=config.train_epochs,
                        epochs_per_iteration=config.train_epochs,
                        batch_size=config.batch_size,
                        learning_rate=config.learning_rate,
                        seed=iteration_seed,
                        shuffle_seed=iteration_seed + 17,
                        max_seconds=phase_budget(0.5),
                        iteration=iteration,
                        reward_profile=config.reward_profile,
                        reward_schedule_version=RewardProfile.for_iteration(iteration).schedule_version,
                        recent_fraction=config.recent_fraction,
                        tactical_fraction=config.tactical_fraction,
                        max_examples_per_epoch=config.max_examples_per_epoch,
                    ),
                    output_dir / "training-checkpoints",
                )
                save_checkpoint(candidate, candidate_path, last_seed=iteration_seed, training_metrics=training_history[-1] if training_history else None)
                save_checkpoint(candidate, latest_candidate_path, last_seed=iteration_seed, training_metrics=training_history[-1] if training_history else None)
                manifest["active_training_history"] = training_history
                manifest["candidate_checkpoint_sha256"] = _sha256(candidate_path)
                manifest["phase"] = "training-complete"
                manifest["completed_phase"] = "training"
                _write_json(manifest_path, manifest)
            if deadline_expired():
                raise TimeoutError("deadline after training")

            manifest["phase"] = "evaluation"
            _write_json(manifest_path, manifest)
            evaluation = evaluate_match(candidate, champion, games=config.eval_games, simulations=config.simulations, max_ply=config.max_ply, seed=iteration_seed + 101, time_limit_seconds=move_time_budget(0.5, config.eval_games * config.max_ply), tactical_plies=0)
            evaluation["tactical_suite"] = evaluate_tactical_suite(candidate, simulations=max(1, min(config.simulations, 4)), seed=iteration_seed + 303, tactical_plies=0)
            tactical_live = evaluate_tactical_suite(candidate, simulations=max(1, min(config.simulations, 4)), seed=iteration_seed + 404, tactical_plies=config.tactical_plies)
            champion_evaluation = evaluate_match(champion, candidate, games=config.eval_games, simulations=config.simulations, max_ply=config.max_ply, seed=iteration_seed + 202, time_limit_seconds=move_time_budget(0.5, config.eval_games * config.max_ply), tactical_plies=0) if config.eval_games >= 20 else None
            if champion_evaluation is not None:
                champion_evaluation["tactical_suite"] = evaluate_tactical_suite(champion, simulations=max(1, min(config.simulations, 4)), seed=iteration_seed + 505, tactical_plies=0)
            promoted = champion_evaluation is not None and promotion_gates(evaluation, champion_evaluation)
            record = {
                "iteration": iteration,
                "iteration_seed": iteration_seed,
                "reward_profile": config.reward_profile,
                "reward_schedule_version": RewardProfile.for_iteration(iteration).schedule_version,
                "self_play": asdict(self_play_stats),
                "training": training_history,
                "training_base": self_play_network.version,
                "evaluation": evaluation,
                "tactical_live_evaluation": tactical_live,
                "champion_evaluation": champion_evaluation,
                "candidate_checkpoint": str(candidate_path),
                "candidate_checkpoint_sha256": _sha256(candidate_path),
                "promoted": promoted,
                "champion_before": champion.version,
            }
            with metrics_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            results.append(record)
            manifest.setdefault("iterations", []).append(record)
            manifest["completed_self_play_games"] = completed_self_play_games
            manifest["latest_candidate"] = str(latest_candidate_path)
            manifest["phase"] = "iteration-complete"
            manifest["completed_phase"] = "evaluation"
            if promoted:
                champion = candidate
                champion.version = f"champion-iteration-{iteration}"
                training_base = champion
                save_checkpoint(champion, champion_path, last_seed=iteration_seed, training_metrics=training_history[-1] if training_history else None)
            elif config.continue_candidate:
                training_base = candidate
            elif config.checkpoint_every_iteration:
                save_checkpoint(champion, champion_path)
            manifest["champion_checkpoint_sha256"] = _sha256(champion_path)
            manifest["replay_sources"] = _source_counts(replay)
            manifest["replay_sha256"] = _sha256(replay_path)
            manifest["updated_at"] = _now()
            _write_json(manifest_path, manifest)
            print(f"[campaign] completed iteration={iteration} self_train={completed_self_play_games}/{target_self_play_games if target_self_play_games is not None else 'unbounded'} candidate_score={evaluation['score']:.3f} promoted={promoted}", flush=True)
            iteration += 1
            resume_phase = None
    except (KeyboardInterrupt, TimeoutError, RuntimeError, OSError, ValueError) as exc:
        interrupted = isinstance(exc, (KeyboardInterrupt, TimeoutError))
        manifest["status"] = "interrupted" if interrupted else "failed"
        manifest["termination_reason"] = str(exc)
        interrupted_path = output_dir / "interrupted.npz"
        champion.version = f"interrupted-{start_iteration:04d}"
        save_checkpoint(champion, interrupted_path)
        replay.save_jsonl(replay_path)
        manifest["interrupted_checkpoint_sha256"] = _sha256(interrupted_path)
    finally:
        if not champion_path.exists():
            save_checkpoint(champion, champion_path)
        replay.save_jsonl(replay_path)
        manifest["completed_self_play_games"] = completed_self_play_games
        if latest_candidate_path is not None:
            manifest["latest_candidate"] = str(latest_candidate_path)
        if not interrupted and manifest.get("status") == "running":
            manifest["status"] = "completed"
            manifest["termination_reason"] = "target-reached" if target_self_play_games is not None and completed_self_play_games >= target_self_play_games else "deadline"
        manifest["replay_sources"] = _source_counts(replay)
        manifest["replay_sha256"] = _sha256(replay_path)
        manifest["updated_at"] = _now()
        _write_json(manifest_path, manifest)
    return {
        "output_dir": str(output_dir),
        "iterations": results,
        "champion": str(champion_path),
        "latest_candidate": str(latest_candidate_path) if latest_candidate_path is not None else manifest.get("latest_candidate"),
        "replay": str(replay_path),
        "manifest": str(manifest_path),
        "metrics": str(metrics_path),
        "interrupted": interrupted,
        "status": manifest.get("status"),
        "resume_fallback": fallback,
        "initial_checkpoint_fallback": bool(manifest.get("initial_checkpoint_fallback", False)),
        "completed_self_play_games": completed_self_play_games,
        "target_self_play_games": target_self_play_games,
    }
