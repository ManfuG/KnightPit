from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

from .board import BoardState, ChessEnvironment, Move
from .encoding import legal_policy
from .model import PolicyValueNetwork
from .reward import RewardEvaluator


@dataclass
class MCTSNode:
    board: BoardState
    parent: "MCTSNode | None" = None
    move: Move | None = None
    prior: float = 0.0
    visits: int = 0
    value_sum: float = 0.0
    children: dict[str, "MCTSNode"] = field(default_factory=dict)

    @property
    def value(self) -> float:
        return self.value_sum / self.visits if self.visits else 0.0

    def expand(self, priors: dict[str, float]) -> None:
        for uci, prior in priors.items():
            if uci not in self.children:
                move = Move.from_uci(uci)
                self.children[uci] = MCTSNode(self.board.push(move), self, move, float(prior))


@dataclass(frozen=True)
class SearchStats:
    requested_simulations: int
    completed_simulations: int
    timed_out: bool
    tactical_extensions: int
    root_children: int


class MCTS:
    def __init__(
        self,
        network: PolicyValueNetwork,
        simulations: int = 32,
        exploration: float = 1.4,
        time_limit_seconds: float | None = None,
        evaluator: RewardEvaluator | None = None,
        heuristic_weight: float = 0.0,
        tactical_plies: int = 0,
    ) -> None:
        self.network = network
        self.simulations = max(1, int(simulations))
        self.exploration = float(exploration)
        self.time_limit_seconds = time_limit_seconds
        self.evaluator = evaluator
        self.heuristic_weight = max(0.0, min(1.0, float(heuristic_weight)))
        self.tactical_plies = max(0, int(tactical_plies))
        self._cache: dict[str, MCTSNode] = {}
        self._root: MCTSNode | None = None
        self.last_search_stats = SearchStats(self.simulations, 0, False, 0, 0)

    @staticmethod
    def _terminal_value(board: BoardState) -> float | None:
        environment = ChessEnvironment(board)
        if not environment.is_terminal():
            return None
        return environment.result_white_perspective() * (1.0 if board.turn == "white" else -1.0)

    @staticmethod
    def _forcing_moves(board: BoardState) -> list[tuple[Move, int]]:
        forcing: list[tuple[Move, int]] = []
        opponent = "black" if board.turn == "white" else "white"
        for move in board.legal_moves():
            captured = board.squares[move.to_square]
            is_capture = captured is not None and captured.color == opponent
            if move.is_en_passant or move.promotion or is_capture:
                priority = 1
            else:
                priority = 0
            next_board = board.push(move)
            status = ChessEnvironment(next_board).status().kind
            if status == "check":
                priority = max(priority, 2)
            elif status == "checkmate":
                priority = 4
            if priority:
                forcing.append((move, priority))
        return forcing

    @classmethod
    def _best_forcing_move(cls, board: BoardState) -> Move | None:
        forcing = cls._forcing_moves(board)
        if not forcing:
            return None
        return max(forcing, key=lambda item: (item[1], item[0].uci()))[0]
    @classmethod
    def _best_forcing_with_priors(cls, board: BoardState, priors: dict[str, float]) -> Move | None:
        forcing = cls._forcing_moves(board)
        if not forcing:
            return None
        highest = max(priority for _, priority in forcing)
        candidates = [move for move, priority in forcing if priority == highest]
        return max(candidates, key=lambda move: (priors.get(move.uci(), 0.0), move.uci()))

    def _select_child(self, node: MCTSNode) -> MCTSNode:
        scale = math.sqrt(max(1, node.visits))
        return max(
            node.children.values(),
            key=lambda child: -child.value + self.exploration * child.prior * scale / (1 + child.visits),
        )

    def _root_for(self, board: BoardState) -> MCTSNode:
        key = board.fen()
        if self._root is not None and self._root.board.fen() == key:
            return self._root
        root = self._cache.get(key)
        if root is None:
            root = MCTSNode(board)
            self._cache[key] = root
        root.parent = None
        self._root = root
        return root

    def advance(self, move: str) -> None:
        """Reuse the searched subtree after a move, when it is available."""
        if self._root is None:
            return
        child = self._root.children.get(move)
        if child is None:
            self._root = None
            return
        child.parent = None
        self._root = child
        self._cache[child.board.fen()] = child

    def search(
        self,
        board: BoardState,
        add_dirichlet_noise: bool = False,
        rng: random.Random | None = None,
        time_limit_seconds: float | None = None,
        ply: int = 0,
    ) -> dict[str, int]:
        root = self._root_for(board)
        requested = self.simulations
        extensions = 0
        if self._terminal_value(root.board) is not None:
            self.last_search_stats = SearchStats(requested, 0, False, 0, 0)
            return {}
        prediction = self.network.predict(root.board)
        priors = legal_policy(root.board, prediction.logits, temperature=1.0)
        if add_dirichlet_noise and priors:
            randomizer = rng or random.Random()
            keys = list(priors)
            noise = [randomizer.gammavariate(0.3, 1.0) for _ in keys]
            total = sum(noise) or 1.0
            for key, value in zip(keys, noise):
                priors[key] = 0.75 * priors[key] + 0.25 * value / total
        root.expand(priors)
        if not root.children:
            self.last_search_stats = SearchStats(requested, 0, False, 0, 0)
            return {}
        budget = self.time_limit_seconds if time_limit_seconds is None else time_limit_seconds
        deadline = time.monotonic() + budget if budget is not None and budget > 0 else None
        preferred_root = self._best_forcing_with_priors(root.board, priors) if self.tactical_plies else None
        completed = 0
        while completed < requested and (deadline is None or time.monotonic() < deadline):
            node = root
            depth = 0
            if preferred_root is not None and preferred_root.uci() in root.children:
                node = root.children[preferred_root.uci()]
                depth = 1
                extensions += 1
            else:
                while node.children:
                    node = self._select_child(node)
                    depth += 1
            remaining_tactical = self.tactical_plies
            while remaining_tactical and self._terminal_value(node.board) is None:
                forced = self._best_forcing_move(node.board)
                if forced is None:
                    break
                child = node.children.get(forced.uci())
                if child is None:
                    child = MCTSNode(node.board.push(forced), node, forced, 1.0)
                    node.children[forced.uci()] = child
                node = child
                depth += 1
                remaining_tactical -= 1
                extensions += 1
            terminal = self._terminal_value(node.board)
            if terminal is None:
                prediction = self.network.predict(node.board)
                priors = legal_policy(node.board, prediction.logits, temperature=1.0)
                node.expand(priors)
                value = prediction.value
                if self.evaluator is not None and self.heuristic_weight:
                    heuristic = self.evaluator.evaluate_position(node.board, node.board.turn, ply + depth).potential
                    value = (1.0 - self.heuristic_weight) * value + self.heuristic_weight * heuristic
            else:
                value = terminal
            if not math.isfinite(value):
                value = 0.0
            while node is not None:
                node.visits += 1
                node.value_sum += value
                value = -value
                node = node.parent
            completed += 1
        timed_out = deadline is not None and completed < requested
        self.last_search_stats = SearchStats(requested, completed, timed_out, extensions, len(root.children))
        return {uci: child.visits for uci, child in root.children.items()}


def choose_move(counts: dict[str, int], temperature: float, rng: random.Random) -> str:
    if not counts:
        raise ValueError("MCTS returned no legal moves")
    if temperature <= 0:
        best = max(counts.values())
        choices = sorted(move for move, visits in counts.items() if visits == best)
        return choices[rng.randrange(len(choices))]
    weighted = []
    total = 0.0
    exponent = 1.0 / temperature
    for move, visits in sorted(counts.items()):
        weight = max(0.0, float(visits)) ** exponent
        total += weight
        weighted.append((total, move))
    if total <= 0:
        return sorted(counts)[rng.randrange(len(counts))]
    threshold = rng.random() * total
    for cumulative, move in weighted:
        if threshold <= cumulative:
            return move
    return weighted[-1][1]
