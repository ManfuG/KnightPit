"""Prepare a local, untrained development model without a training campaign."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from knightpit_ai.model import PolicyValueNetwork


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--create", action="store_true", help="Create a seeded model only if the file is absent")
    args = parser.parse_args()
    if not args.checkpoint.exists() and args.create:
        model = PolicyValueNetwork(seed=42)
        model.version = "development-seed-42"
        temporary = args.checkpoint.with_suffix(".tmp.npz")
        try:
            model.save_checkpoint(temporary)
            PolicyValueNetwork.load_checkpoint(temporary)
            temporary.replace(args.checkpoint)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Created untrained development checkpoint (seed 42): {args.checkpoint}")
    else:
        PolicyValueNetwork.load_checkpoint(args.checkpoint)
        print(f"Reusing checkpoint: {args.checkpoint}")


if __name__ == "__main__":
    main()
