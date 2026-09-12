# KnightPitAI

KnightPitAI is a small, educational, CPU-only chess AI designed to integrate with the KnightPit frontend. It contains the chess environment, representation, model, search, self-play, training, evaluation, checkpoint, campaign, and local API layers in one independently testable Python package.

The implementation is intentionally modest: it is designed to be runnable and reproducible without CUDA or a dedicated GPU. It is not intended to compete with Stockfish or to claim a particular playing strength.

## License and provenance

Project source code, tests, configuration, and project-generated training artifacts are released under the MIT License. Dependencies retain their upstream terms; resolved versions, hashes, URLs, and notable license obligations are documented in the lockfiles and in [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). No dependency source is vendored.

The project does not include Stockfish, another external chess engine, tablebases, or an unverified game dataset. Self-play replays, checkpoints, caches, and local campaign outputs are generated artifacts and remain ignored by Git.

## Reproducible installation

The locked CPU runtime supports Python **3.10–3.13**. For the integrated application, run `npm install` then `npm run dev` from the repository root: the launcher prepares a reusable environment and a seed-42 development checkpoint automatically. `npm run bootstrap` prepares them without starting servers; no environment activation is required. See the [root quick start](../README.md#quick-start) for prerequisites, recovery commands, and overrides.

For manual backend installation, the lockfiles were generated with hashed requirements:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-cpu.lock
$env:PYTHONPATH = "$PWD/src"
```

On POSIX, activate with `. .venv/bin/activate` and use `export PYTHONPATH="$PWD/src"`. Run manual backend commands below from this directory.

Install the test dependencies when working on the package:

```powershell
python -m pip install --require-hashes -r requirements-test.lock
```

Run the publication audit before distributing a checkout:

```powershell
python tools/check_publication.py
```

The audit rejects external-engine references, datasets, unexpected binaries or archives, generated artifacts outside the ignored output roots, unreadable files, and oversized checkpoints.

## Architecture

- `src/knightpit_ai/board.py`: project-owned chess rules, FEN and UCI conversion, legal-move validation, castling, en passant, promotion, checkmate, stalemate, insufficient material, and draw counters. Moves are applied through `ChessEnvironment.apply_uci()`.
- `src/knightpit_ai/encoding.py`: the stable 18-plane `8x8` board representation and move-index space.
- `src/knightpit_ai/model.py`: compact NumPy policy/value network and metadata-driven checkpoints containing architecture, seed, replay count, and recent losses.
- `src/knightpit_ai/mcts.py`: CPU PUCT search with FEN caching, subtree reuse, simulation and time limits, and training-only Dirichlet exploration noise.
- `src/knightpit_ai/self_play.py` and `replay_buffer.py`: deterministic replay generation with encoded positions, policy/value targets, seeds, model metadata, reward profiles, and per-game statistics.
- `src/knightpit_ai/reward.py` and `curriculum.py`: bounded project-owned reward components and their scheduled curriculum.
- `src/knightpit_ai/train.py`: interruptible mini-batch training, seeded shuffling, deadline and finite-value checks, and safety checkpoints.
- `src/knightpit_ai/campaign.py`: resumable iterative training with champion/candidate checkpoints, alternating-color evaluation, metrics, and anti-regression gates.
- `src/knightpit_ai/api.py`: local FastAPI service with `GET /health` and `POST /predict`.

## Self-play, training, and evaluation

```powershell
python -m knightpit_ai self-play --games 8 --simulations 4 --max-ply 80 --seed 42 --output data/generated/smoke.jsonl
python -m knightpit_ai train --epochs 2 --batch-size 32 --data data/generated/smoke.jsonl
python -m knightpit_ai evaluate --games 20 --seed 42 --checkpoint checkpoints/knightpit-epoch-0001.npz
python -m knightpit_ai inspect-checkpoint --checkpoint checkpoints/knightpit-epoch-0001.npz
```

A replay manifest is written next to each JSONL replay. Terminal outcomes remain authoritative. Bounded material, center-control, and development potentials may be used for early max-ply positions according to the selected reward schedule; the terminal result always takes precedence.

## CPU campaign

The campaign stores `champion.npz`, candidate checkpoints, replay data, metrics, and a manifest in the ignored output directory. A previous champion is kept when a candidate fails its evaluation gates.

```powershell
python -m knightpit_ai train-campaign --minutes 60 --seed 42 --reward-profile principles-v1 --output-dir data/generated/campaign-60m
python -m knightpit_ai train-campaign --minutes 60 --seed 42 --reward-profile principles-v1 --output-dir data/generated/campaign-60m --resume
```

Integrated development does not require a campaign: the root launcher creates a small **untrained** seeded checkpoint only when no existing model is available. Training remains optional; to run a short smoke campaign manually:

```powershell
python -m knightpit_ai train-campaign --minutes 0.1 --games-per-iteration 2 --simulations 2 --max-ply 24 --eval-games 4 --seed 42 --output-dir .campaign-smoke
```

Manifests and metrics record global and derived seeds, code/configuration version, timestamps, CPU mode, reward policy, and resume behavior. Interrupted campaigns write an interruption checkpoint and can be resumed without discarding the available champion or replay data.

## Local API

```powershell
$env:KNIGHTPIT_CHECKPOINT = "data/generated/campaign-60m/champion.npz"
python -m knightpit_ai.api
```

`GET /health` reports whether a model is loaded. `POST /predict` accepts a FEN position, a UCI history, and a time budget, then returns a move, evaluation, model version, and legality flag. Invalid FEN, illegal moves, terminal positions, and missing checkpoints are rejected with explicit HTTP status codes.

## Tests and publication checks

```powershell
python -m pytest
python tools/check_publication.py
```

The test suite covers chess rules, encoding and move-space stability, deterministic self-play, checkpoint round trips, reward metadata, API inference, invalid inputs, terminal positions, and missing models. The tactical fixtures verify representative mate, capture, and promotion choices; they do not establish competitive playing strength.

## Development disclosure

This project was developed with **GPT-5.6-Luna** using **Oh My Pi** as the coding harness. This is a workflow disclosure only and does not modify the MIT license or the upstream licenses of dependencies and assets.
