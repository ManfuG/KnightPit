from __future__ import annotations

import json
import random
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np


@dataclass
class ReplayExample:
    """One self-play training position with reproducibility provenance."""

    features: np.ndarray
    policy: dict[str, float]
    value: float
    position: str | None = None
    seed: int | None = None
    game_index: int | None = None
    model_version: str = "untrained"
    source: str = "self-play"
    target_kind: str = "terminal"
    self_play_config: dict[str, Any] = field(default_factory=dict)
    reward_components: dict[str, float] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "features": np.asarray(self.features, dtype=np.float32).tolist(),
            "policy": self.policy,
            "value": float(self.value),
            "seed": self.seed,
            "game_index": self.game_index,
            "model_version": self.model_version,
            "source": self.source,
            "target_kind": self.target_kind,
            "self_play_config": self.self_play_config,
            "reward_components": {str(k): float(v) for k, v in self.reward_components.items()},
        }

    @property
    def deduplication_key(self) -> str | None:
        if self.position is None:
            return None
        fen_parts = self.position.split()
        side = fen_parts[1] if len(fen_parts) > 1 else ""
        return f"{fen_parts[0]} {side}|{self.target_kind}"

    @property
    def is_tactical(self) -> bool:
        return self.source == "tactical-curriculum"

    @property
    def is_self_play(self) -> bool:
        return self.source == "self-play"

    @property
    def age_group(self) -> str:
        return str(self.self_play_config.get("age_group", "recent"))

class ReplayBuffer:
    def __init__(self, capacity: int = 10_000) -> None:
        if capacity < 1:
            raise ValueError("replay capacity must be positive")
        self.capacity = int(capacity)
        self._items: deque[ReplayExample] = deque(maxlen=self.capacity)
        self._keys: dict[str, ReplayExample] = {}

    def add(self, example: ReplayExample) -> None:
        key = example.deduplication_key
        if key is not None and key in self._keys:
            self._items = deque((item for item in self._items if item.deduplication_key != key), maxlen=self.capacity)
        self._items.append(example)
        if key is not None:
            self._keys[key] = example
        while len(self._keys) > len(self._items):
            self._keys = {item.deduplication_key: item for item in self._items if item.deduplication_key is not None}

    def extend(self, examples: Iterable[ReplayExample]) -> None:
        for example in examples:
            self.add(example)

    def sample(self, size: int, rng: random.Random) -> list[ReplayExample]:
        return rng.sample(list(self._items), min(max(0, size), len(self._items)))

    def sample_for_training(
        self,
        size: int,
        rng: random.Random,
        recent_fraction: float = 0.60,
        tactical_fraction: float = 0.20,
    ) -> tuple[list[ReplayExample], dict[str, int]]:
        if not 0.0 <= recent_fraction <= 1.0 or not 0.0 <= tactical_fraction <= 1.0:
            raise ValueError("training fractions must be between zero and one")
        if recent_fraction + tactical_fraction > 1.0:
            raise ValueError("recent and tactical fractions cannot exceed one")
        items = list(self._items)
        if not items or size <= 0:
            return [], {"self-play-recent": 0, "self-play-old": 0, "tactical-curriculum": 0, "other": 0}
        tactical = [item for item in items if item.is_tactical]
        self_play = [item for item in items if item.is_self_play]
        explicit_recent = [item for item in self_play if item.age_group == "recent"]
        explicit_old = [item for item in self_play if item.age_group == "old"]
        if not explicit_recent and self_play:
            split = max(1, len(self_play) // 2)
            explicit_old = self_play[: len(self_play) - split]
            explicit_recent = self_play[len(self_play) - split :]
        elif not explicit_old:
            split = max(1, len(explicit_recent) // 2)
            explicit_old = explicit_recent[: len(explicit_recent) - split]
            explicit_recent = explicit_recent[len(explicit_recent) - split :]
        other = [item for item in items if not item.is_tactical and not item.is_self_play]
        requested = {
            "self-play-recent": round(size * recent_fraction),
            "self-play-old": round(size * (1.0 - recent_fraction - tactical_fraction)),
            "tactical-curriculum": round(size * tactical_fraction),
        }
        requested["other"] = max(0, size - sum(requested.values()))
        pools = {
            "self-play-recent": explicit_recent,
            "self-play-old": explicit_old,
            "tactical-curriculum": tactical,
            "other": other,
        }
        selected: list[ReplayExample] = []
        counts = {key: 0 for key in pools}
        remaining = size
        for key in ("self-play-recent", "self-play-old", "tactical-curriculum", "other"):
            take = min(requested[key], len(pools[key]), remaining)
            if take:
                chosen = rng.sample(pools[key], take)
                selected.extend(chosen)
                counts[key] += take
                remaining -= take
        if remaining:
            available_ids = {id(selected_item) for selected_item in selected}
            available = [item for item in items if id(item) not in available_ids]
            for item in rng.sample(available, min(remaining, len(available))):
                selected.append(item)
                if item.is_tactical:
                    counts["tactical-curriculum"] += 1
                elif item.is_self_play and item.age_group == "old":
                    counts["self-play-old"] += 1
                elif item.is_self_play:
                    counts["self-play-recent"] += 1
                else:
                    counts["other"] += 1
        rng.shuffle(selected)
        return selected, counts

    def __len__(self) -> int:
        return len(self._items)


    def save_jsonl(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            for item in self._items:
                handle.write(json.dumps(item.to_record(), separators=(",", ":"), sort_keys=True) + "\n")
        return destination

    @classmethod
    def load_jsonl(cls, path: str | Path, capacity: int = 10_000) -> "ReplayBuffer":
        buffer = cls(capacity)
        source = Path(path)
        if not source.exists() or source.stat().st_size == 0:
            return buffer
        with source.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    features = data.get("features", data.get("position_encoding"))
                    if features is None or not isinstance(data.get("policy"), dict):
                        continue
                    self_play_config = dict(data.get("self_play_config", {}))
                    reward_components = dict(data.get("reward_components", {}))
                    legacy = "source" not in data or "target_kind" not in data or "reward_components" not in data
                    if legacy:
                        self_play_config["reward_profile"] = "legacy-material"
                    buffer.add(
                        ReplayExample(
                            np.asarray(features, dtype=np.float32),
                            {str(k): float(v) for k, v in data["policy"].items()},
                            float(data["value"]),
                            position=data.get("position"),
                            seed=data.get("seed"),
                            game_index=data.get("game_index"),
                            model_version=str(data.get("model_version", "untrained")),
                            source="legacy" if legacy else str(data.get("source", "self-play")),
                            target_kind="legacy" if legacy else str(data.get("target_kind", "terminal")),
                            self_play_config=self_play_config,
                            reward_components={str(k): float(v) for k, v in reward_components.items()},
                        )
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    continue
        return buffer
