from __future__ import annotations

import argparse
import json
from pathlib import Path

from .campaign import CampaignConfig, run_campaign
from .evaluate import evaluate_network
from .model import PolicyValueNetwork
from .replay_buffer import ReplayBuffer
from .self_play import SelfPlayConfig, generate_self_play
from .train import TrainingConfig, train_network


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m knightpit_ai", description="KnightPit CPU-only chess AI")
    commands = parser.add_subparsers(dest="command", required=True)
    self_play = commands.add_parser("self-play", help="generate legal self-play games")
    self_play.add_argument("--games", type=int, default=8)
    self_play.add_argument("--simulations", type=int, default=16)
    self_play.add_argument("--max-ply", type=int, default=240)
    self_play.add_argument("--temperature", type=float, default=1.0)
    self_play.add_argument("--seed", type=int, default=42)
    self_play.add_argument("--output", default="data/generated/replay.jsonl")
    self_play.add_argument("--checkpoint")
    self_play.add_argument("--reward-profile", choices=("principles-v1",), default="principles-v1")
    train = commands.add_parser("train", help="train from generated replay data")
    train.add_argument("--epochs", type=int, default=2)
    train.add_argument("--batch-size", type=int, default=32)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--data", default="data/generated/replay.jsonl")
    train.add_argument("--checkpoint-dir", default="checkpoints")
    train.add_argument("--checkpoint")
    evaluate = commands.add_parser("evaluate", help="measure legal self-play behavior")
    evaluate.add_argument("--games", type=int, default=20)
    evaluate.add_argument("--simulations", type=int, default=8)
    evaluate.add_argument("--max-ply", type=int, default=120)
    evaluate.add_argument("--seed", type=int, default=42)
    evaluate.add_argument("--checkpoint")
    campaign = commands.add_parser("train-campaign", help="run an interruptible champion-gated campaign")
    campaign.add_argument("--minutes", type=float, default=60.0)
    campaign.add_argument("--no-time-limit", action="store_true")
    campaign.add_argument("--total-self-play-games", type=int, default=512)
    campaign.add_argument("--seed", type=int, default=42)
    campaign.add_argument("--simulations", type=int, default=16)
    campaign.add_argument("--tactical-plies", type=int, default=0)
    campaign.add_argument("--max-ply", type=int, default=240)
    campaign.add_argument("--games-per-iteration", type=int, default=8)
    campaign.add_argument("--replay-capacity", type=int, default=10_000)
    campaign.add_argument("--train-epochs", type=int, default=2)
    campaign.add_argument("--batch-size", type=int, default=32)
    campaign.add_argument("--learning-rate", type=float, default=0.001)
    campaign.add_argument("--max-examples-per-epoch", type=int)
    campaign.add_argument("--eval-games", type=int, default=20)
    campaign.add_argument("--output-dir", default="data/generated/campaign-60m")
    campaign.add_argument("--resume", action="store_true")
    campaign.add_argument("--continue-candidate", action="store_true")
    campaign.add_argument("--reward-profile", choices=("principles-v1",), default="principles-v1")
    campaign.add_argument("--initial-checkpoint")
    campaign.add_argument("--no-checkpoint-every-iteration", dest="checkpoint_every_iteration", action="store_false")
    campaign.set_defaults(checkpoint_every_iteration=True)
    inspect = commands.add_parser("inspect-checkpoint", help="print checkpoint metadata")
    inspect.add_argument("--checkpoint", default="checkpoints/knightpit-epoch-0001.npz")
    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "self-play":
        network = PolicyValueNetwork(seed=args.seed) if not args.checkpoint else PolicyValueNetwork.load_checkpoint(args.checkpoint)
        config = SelfPlayConfig(
            games=args.games,
            simulations=args.simulations,
            max_ply=args.max_ply,
            temperature=args.temperature,
            seed=args.seed,
            reward_profile=args.reward_profile,
        )
        _, stats = generate_self_play(network, config, args.output)
        print(json.dumps({
            "output": args.output,
            "games": stats.games,
            "completed": stats.completed,
            "plies": stats.plies,
            "legal_move_rate": stats.legal_move_rate,
            "white_wins": stats.white_wins,
            "black_wins": stats.black_wins,
            "draws": stats.draws,
            "terminal_games": stats.terminal_games,
            "max_ply_games": stats.max_ply_games,
            "termination_reasons": stats.termination_reasons,
            "effective_seeds": stats.effective_seeds,
            "captures": stats.captures,
            "white_captures": stats.white_captures,
            "black_captures": stats.black_captures,
            "material_delta_average": stats.material_delta_average,
            "opening_center_average": stats.opening_center_average,
            "opening_development_average": stats.opening_development_average,
        }, indent=2))
        return 0
    if args.command == "train":
        replay = ReplayBuffer.load_jsonl(args.data)
        network = PolicyValueNetwork(seed=args.seed) if not args.checkpoint else PolicyValueNetwork.load_checkpoint(args.checkpoint)
        history = train_network(network, replay, TrainingConfig(epochs=args.epochs, batch_size=args.batch_size, seed=args.seed), args.checkpoint_dir)
        print(json.dumps({"data": args.data, "examples": len(replay), "history": history}, indent=2))
        return 0
    if args.command == "evaluate":
        network = PolicyValueNetwork(seed=args.seed) if not args.checkpoint else PolicyValueNetwork.load_checkpoint(args.checkpoint)
        metrics = evaluate_network(network, games=args.games, simulations=args.simulations, max_ply=args.max_ply, seed=args.seed)
        print(json.dumps(metrics, indent=2))
        return 0
    if args.command == "train-campaign":
        result = run_campaign(
            CampaignConfig(
                minutes=None if args.no_time_limit else args.minutes,
                seed=args.seed,
                simulations=args.simulations,
                tactical_plies=args.tactical_plies,
                max_ply=args.max_ply,
                games_per_iteration=args.games_per_iteration,
                replay_capacity=args.replay_capacity,
                train_epochs=args.train_epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
                max_examples_per_epoch=args.max_examples_per_epoch,
                eval_games=args.eval_games,
                checkpoint_every_iteration=args.checkpoint_every_iteration,
                resume=args.resume,
                output_dir=args.output_dir,
                reward_profile=args.reward_profile,
                initial_checkpoint=args.initial_checkpoint,
                total_self_play_games=args.total_self_play_games,
                no_time_limit=args.no_time_limit,
                continue_candidate=args.continue_candidate,
            )
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "inspect-checkpoint":
        network = PolicyValueNetwork.load_checkpoint(args.checkpoint)
        print(json.dumps({"checkpoint": str(Path(args.checkpoint)), "model_version": network.version, "step": network.step, "hidden_size": network.hidden_size, "policy_rank": network.policy_rank, "seed": network.seed, "training_metrics": network.last_metrics}, indent=2))
        return 0
    return 1


def main() -> None:
    raise SystemExit(run(build_parser().parse_args()))
