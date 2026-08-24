from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

from .model import PolicyValueNetwork
from .replay_buffer import ReplayBuffer


@dataclass(frozen=True)
class TrainingConfig:
    epochs: int = 2
    batch_size: int = 32
    learning_rate: float = 0.01
    seed: int = 42
    shuffle_seed: int | None = None
    checkpoint_every: int = 1
    max_seconds: float | None = None
    epochs_per_iteration: int | None = None
    iteration: int = 1
    reward_profile: str | None = None
    reward_schedule_version: str | None = None
    recent_fraction: float = 0.60
    tactical_fraction: float = 0.20
    max_examples_per_epoch: int | None = None


def _finite_metrics(metrics: dict[str, float]) -> bool:
    return all(math.isfinite(float(value)) for value in metrics.values())


def train_network(
    network: PolicyValueNetwork,
    replay: ReplayBuffer,
    config: TrainingConfig,
    checkpoint_dir: str | Path = "checkpoints",
) -> list[dict[str, object]]:
    if len(replay) == 0:
        raise ValueError("replay buffer is empty; generate self-play data first")
    if config.batch_size < 1 or config.epochs < 1:
        raise ValueError("batch size and epochs must be positive")
    if config.max_examples_per_epoch is not None and config.max_examples_per_epoch < 1:
        raise ValueError("max_examples_per_epoch must be positive")
    rng = random.Random(config.shuffle_seed if config.shuffle_seed is not None else config.seed)
    history: list[dict[str, object]] = []
    directory = Path(checkpoint_dir)
    directory.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + config.max_seconds if config.max_seconds and config.max_seconds > 0 else None
    epochs = config.epochs_per_iteration or config.epochs
    for epoch in range(1, epochs + 1):
        if deadline is not None and time.monotonic() >= deadline:
            break
        examples, source_counts = replay.sample_for_training(
            config.max_examples_per_epoch or len(replay),
            rng,
            recent_fraction=config.recent_fraction,
            tactical_fraction=config.tactical_fraction,
        )
        losses: list[dict[str, float]] = []
        try:
            for offset in range(0, len(examples), config.batch_size):
                if deadline is not None and time.monotonic() >= deadline:
                    break
                batch = examples[offset : offset + config.batch_size]
                metrics = network.train_batch(
                    ((item.features, item.policy, item.value) for item in batch),
                    config.learning_rate,
                )
                if not _finite_metrics(metrics):
                    raise FloatingPointError("non-finite training metrics")
                losses.append(metrics)
        except (FloatingPointError, ValueError, OverflowError) as exc:
            network.version = f"safety-iteration-{config.iteration:04d}"
            network.save_checkpoint(
                directory / f"safety-iteration-{config.iteration:04d}.npz",
                seed=config.seed,
                replay_examples=len(replay),
                last_seed=config.shuffle_seed if config.shuffle_seed is not None else config.seed,
                reward_profile=config.reward_profile,
                reward_schedule_version=config.reward_schedule_version,
            )
            raise RuntimeError(f"training stopped after non-finite batch: {exc}") from exc
        if not losses:
            break
        total = sum(item["examples"] for item in losses) or 1.0
        metrics: dict[str, object] = {
            "epoch": float(epoch),
            "iteration": float(config.iteration),
            "policy_loss": sum(item["policy_loss"] * item["examples"] for item in losses) / total,
            "value_loss": sum(item["value_loss"] * item["examples"] for item in losses) / total,
            "examples": total,
            "source_counts": source_counts,
        }
        numeric = {key: float(value) for key, value in metrics.items() if key != "source_counts"}
        if not _finite_metrics(numeric):
            raise RuntimeError("non-finite aggregate training metrics")
        history.append(metrics)
        if epoch % config.checkpoint_every == 0:
            network.version = f"iteration-{config.iteration:04d}-epoch-{epoch:04d}"
            network.save_checkpoint(
                directory / f"knightpit-{network.version}.npz",
                seed=config.seed,
                replay_examples=len(replay),
                last_seed=config.shuffle_seed if config.shuffle_seed is not None else config.seed,
                reward_profile=config.reward_profile,
                reward_schedule_version=config.reward_schedule_version,
            )
    return history
