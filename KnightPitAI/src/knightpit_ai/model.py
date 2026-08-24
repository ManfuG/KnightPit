from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

from .board import BoardState, Move
from .encoding import MOVE_SPACE_SIZE, encode_board, move_to_index


class Prediction:
    def __init__(self, logits: np.ndarray, value: float) -> None:
        self.logits = logits
        self.value = value


class PolicyValueNetwork:
    """Tiny NumPy MLP with a low-rank legal-move policy head."""

    def __init__(self, seed: int = 0, hidden_size: int = 32, policy_rank: int = 8, learning_rate: float = 0.01) -> None:
        self.hidden_size = hidden_size
        self.policy_rank = policy_rank
        self.learning_rate = learning_rate
        self.input_size = 18 * 8 * 8
        rng = np.random.default_rng(seed)
        self.features_w = (rng.standard_normal((hidden_size, self.input_size)) * np.sqrt(2.0 / self.input_size)).astype(np.float32)
        self.features_b = np.zeros(hidden_size, dtype=np.float32)
        self.policy_move_w = (rng.standard_normal((MOVE_SPACE_SIZE, policy_rank)) * np.sqrt(2.0 / policy_rank)).astype(np.float32)
        self.policy_context = (rng.standard_normal((policy_rank, hidden_size)) * np.sqrt(2.0 / hidden_size)).astype(np.float32)
        self.policy_b = np.zeros(MOVE_SPACE_SIZE, dtype=np.float32)
        self.value_w = (rng.standard_normal(hidden_size) * np.sqrt(2.0 / hidden_size)).astype(np.float32)
        self.value_b = np.float32(0.0)
        self.version = "untrained"
        self.step = 0
        self.seed = seed
        self.last_metrics: dict[str, float] = {}

    def _features(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        flat = np.asarray(features, dtype=np.float32).reshape(-1)
        hidden_pre = np.clip(self.features_w @ flat + self.features_b, -20.0, 20.0)
        hidden = np.maximum(hidden_pre, 0.0)
        value = float(np.tanh(np.clip(self.value_w @ hidden + self.value_b, -20.0, 20.0)))
        return flat, hidden, value

    def _legal_scores(self, board: BoardState, hidden: np.ndarray) -> tuple[list[Move], np.ndarray]:
        legal = board.legal_moves()
        if not legal:
            return [], np.empty(0, dtype=np.float32)
        indices = np.asarray([move_to_index(move) for move in legal], dtype=np.int64)
        context = self.policy_context @ hidden
        return legal, self.policy_move_w[indices] @ context + self.policy_b[indices]

    def predict(self, board: BoardState) -> Prediction:
        _, hidden, value = self._features(encode_board(board))
        legal, scores = self._legal_scores(board, hidden)
        logits = np.full(MOVE_SPACE_SIZE, -1e9, dtype=np.float32)
        if legal:
            logits[[move_to_index(move) for move in legal]] = scores
        return Prediction(logits=logits, value=value)

    def train_batch(self, examples: Iterable[tuple[np.ndarray, Mapping[str, float], float]], learning_rate: float | None = None) -> dict[str, float]:
        lr = min(self.learning_rate if learning_rate is None else learning_rate, 0.001)
        if not math.isfinite(lr):
            raise FloatingPointError("non-finite learning rate")
        batch_examples = list(examples)
        for features, _, target_value in batch_examples:
            if not np.all(np.isfinite(np.asarray(features))) or not math.isfinite(float(target_value)):
                raise FloatingPointError("non-finite replay example")
        total_policy = total_value = 0.0
        count = 0
        for features, target_policy, target_value in batch_examples:
            flat, hidden, value = self._features(features)
            if not target_policy:
                continue
            uci_moves = list(target_policy)
            indices = np.asarray([move_to_index(Move.from_uci(move)) for move in uci_moves], dtype=np.int64)
            context = np.nan_to_num(self.policy_context @ hidden, nan=0.0, posinf=10.0, neginf=-10.0)
            scores = np.nan_to_num(self.policy_move_w[indices] @ context + self.policy_b[indices], nan=0.0, posinf=20.0, neginf=-20.0)
            shifted = scores.astype(np.float64) - np.max(scores)
            probabilities = np.exp(np.clip(shifted, -60.0, 60.0))
            probabilities /= np.sum(probabilities)
            target = np.asarray([max(0.0, target_policy[move]) for move in uci_moves], dtype=np.float64)
            target_sum = float(target.sum())
            target = target / target_sum if target_sum > 0 else np.full_like(target, 1.0 / len(target))
            policy_loss = -float(np.sum(target * np.log(np.maximum(probabilities, 1e-12))))
            policy_grad = (probabilities - target).astype(np.float32)
            grad_context = np.zeros(self.policy_rank, dtype=np.float32)
            for index, grad in zip(indices, policy_grad):
                grad_context += grad * self.policy_move_w[index]
                self.policy_move_w[index] -= lr * grad * context
                self.policy_b[index] -= lr * grad
            grad_context = np.clip(np.nan_to_num(grad_context), -5.0, 5.0)
            self.policy_context -= lr * np.outer(grad_context, hidden)
            grad_hidden = self.policy_context.T @ grad_context
            value_error = value - float(target_value)
            value_loss = value_error * value_error
            value_grad = np.float32(2.0 * value_error * (1.0 - value * value))
            self.value_w -= lr * value_grad * hidden
            self.value_b -= lr * value_grad
            grad_hidden += value_grad * self.value_w
            grad_hidden[hidden <= 0] = 0.0
            grad_hidden = np.clip(np.nan_to_num(grad_hidden), -5.0, 5.0)
            self.features_w -= lr * np.outer(grad_hidden, flat)
            self.features_b -= lr * grad_hidden
            self.value_w = np.clip(np.nan_to_num(self.value_w), -10.0, 10.0)
            self.features_w = np.clip(np.nan_to_num(self.features_w), -10.0, 10.0)
            self.policy_move_w = np.clip(np.nan_to_num(self.policy_move_w), -10.0, 10.0)
            self.policy_context = np.clip(np.nan_to_num(self.policy_context), -10.0, 10.0)
            total_policy += policy_loss
            total_value += value_loss
            count += 1
            self.step += 1
        if not math.isfinite(total_policy) or not math.isfinite(total_value) or any(
            not np.all(np.isfinite(array))
            for array in (self.features_w, self.features_b, self.policy_move_w, self.policy_context, self.policy_b, self.value_w)
        ):
            raise FloatingPointError("non-finite loss or gradient state")
        if count == 0:
            self.last_metrics = {"policy_loss": 0.0, "value_loss": 0.0, "examples": 0.0}
            return self.last_metrics
        self.last_metrics = {"policy_loss": total_policy / count, "value_loss": total_value / count, "examples": float(count)}
        return self.last_metrics

    def save_checkpoint(
        self,
        path: str | Path,
        step: int | None = None,
        seed: int | None = None,
        replay_examples: int = 0,
        last_seed: int | None = None,
        training_metrics: dict[str, float] | None = None,
        reward_profile: str | None = None,
        reward_schedule_version: str | None = None,
    ) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "format": 4,
            "model": "knightpit-tiny-policy-value",
            "step": self.step if step is None else step,
            "seed": self.seed if seed is None else seed,
            "last_seed": self.seed if last_seed is None else last_seed,
            "hidden_size": self.hidden_size,
            "policy_rank": self.policy_rank,
            "input_size": self.input_size,
            "learning_rate": self.learning_rate,
            "training_metrics": training_metrics or self.last_metrics,
            "version": self.version,
            "replay_examples": int(replay_examples),
            "reward_profile": reward_profile,
            "reward_schedule_version": reward_schedule_version,
            "architecture": {
                "input_size": self.input_size,
                "hidden_size": self.hidden_size,
                "policy_rank": self.policy_rank,
                "policy_space": MOVE_SPACE_SIZE,
            },
        }
        np.savez_compressed(
            destination,
            features_w=self.features_w,
            features_b=self.features_b,
            policy_move_w=self.policy_move_w,
            policy_context=self.policy_context,
            policy_b=self.policy_b,
            value_w=self.value_w,
            value_b=np.asarray(self.value_b),
            metadata=np.asarray(json.dumps(metadata, sort_keys=True)),
        )
        return destination

    @classmethod
    def load_checkpoint(
        cls,
        path: str | Path,
        expected_reward_profile: str | None = None,
        expected_reward_schedule_version: str | None = None,
    ) -> "PolicyValueNetwork":
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        try:
            with np.load(source, allow_pickle=False) as data:
                metadata = json.loads(str(data["metadata"]))
                format_version = int(metadata.get("format", 0))
                if format_version not in {2, 3, 4}:
                    raise ValueError(f"unsupported checkpoint format: {format_version}")
                if expected_reward_profile is not None and metadata.get("reward_profile") not in (None, expected_reward_profile):
                    raise ValueError("checkpoint reward profile mismatch")
                if expected_reward_schedule_version is not None and metadata.get("reward_schedule_version") not in (None, expected_reward_schedule_version):
                    raise ValueError("checkpoint reward schedule mismatch")
                hidden_size = int(metadata["hidden_size"])
                policy_rank = int(metadata.get("policy_rank", 8))
                input_size = int(metadata.get("input_size", 18 * 8 * 8))
                if input_size != 18 * 8 * 8 or hidden_size < 1 or policy_rank < 1:
                    raise ValueError("incompatible checkpoint architecture")
                architecture = metadata.get("architecture", {})
                if architecture and (
                    int(architecture.get("input_size", input_size)) != input_size
                    or int(architecture.get("hidden_size", hidden_size)) != hidden_size
                    or int(architecture.get("policy_rank", policy_rank)) != policy_rank
                    or int(architecture.get("policy_space", MOVE_SPACE_SIZE)) != MOVE_SPACE_SIZE
                ):
                    raise ValueError("checkpoint architecture metadata mismatch")
                expected = {
                    "features_w": (hidden_size, input_size),
                    "features_b": (hidden_size,),
                    "policy_move_w": (MOVE_SPACE_SIZE, policy_rank),
                    "policy_context": (policy_rank, hidden_size),
                    "policy_b": (MOVE_SPACE_SIZE,),
                    "value_w": (hidden_size,),
                }
                for name, shape in expected.items():
                    if name not in data or tuple(data[name].shape) != shape:
                        raise ValueError(f"incompatible checkpoint tensor: {name}")
                model = cls(
                    seed=int(metadata.get("seed", 0) or 0),
                    hidden_size=hidden_size,
                    policy_rank=policy_rank,
                    learning_rate=float(metadata["learning_rate"]),
                )
                model.features_w = data["features_w"].astype(np.float32)
                model.features_b = data["features_b"].astype(np.float32)
                model.policy_move_w = data["policy_move_w"].astype(np.float32)
                model.policy_context = data["policy_context"].astype(np.float32)
                model.policy_b = data["policy_b"].astype(np.float32)
                model.value_w = data["value_w"].astype(np.float32)
                model.value_b = np.float32(data["value_b"])
                model.version = str(metadata.get("version", source.stem))
                model.step = int(metadata.get("step", 0))
                model.seed = metadata.get("seed")
                model.last_metrics = {str(k): float(v) for k, v in metadata.get("training_metrics", {}).items()}
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid checkpoint {source}: {exc}") from exc
        return model
