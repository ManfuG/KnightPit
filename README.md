# KnightPit

KnightPit is an educational, open-source chess application that combines a React/TypeScript interface with a small chess AI written in Python. The project is designed to run on CPU-only hardware and to make the complete training and inference pipeline reproducible and inspectable.

The AI is developed from scratch around a project-owned chess environment, a compact NumPy policy/value network, CPU MCTS with PUCT, and self-play training. A local FastAPI service exposes model inference to the frontend. The browser client sends FEN positions and UCI move history, then validates every response against its own legal-move engine before changing the local game state.

## Features

- Play against KnightPit AI from the web interface.
- Project-owned chess rules with legal-move validation, castling, en passant, promotion, checkmate, stalemate, and draw handling.
- CPU-only self-play, replay generation, training, evaluation, checkpoint inspection, and resumable campaigns.
- Local FastAPI endpoints for health checks and move prediction.
- Training and evaluation metadata with deterministic seeds, model versions, reward profiles, and campaign metrics.
- No Stockfish, external chess engine, tablebase, or unverified game dataset.

## Technology

- **Frontend:** React, TypeScript, React Router, Motion, Tailwind CSS, and Vite.
- **AI service:** Python 3.10+, NumPy, FastAPI, and Uvicorn.
- **Testing:** pytest, FastAPI TestClient, and deterministic smoke scenarios.

## Repository layout

```text
src/                       React application and chess UI
KnightPitAI/src/           Python chess environment, model, MCTS, training, and API
KnightPitAI/tests/         Backend and AI tests
scripts/dev.mjs            Starts the local AI API and Vite together
src/components/chess/    Chess board and Unicode piece glyphs
.github/workflows/         Continuous integration
```
## Requirements

- Node.js 20 or newer.
- Python 3.10 or newer.
- No CUDA-capable GPU is required.


## Quick start

### 1. Install frontend dependencies

```powershell
npm install
```

### 2. Create the Python environment

```powershell
cd KnightPitAI
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-cpu.lock
cd ..
```

For development and tests, install the test lockfile instead:

```powershell
cd KnightPitAI
python -m pip install --require-hashes -r requirements-test.lock
cd ..
```

### 3. Generate a local checkpoint

Generated checkpoints and replay data are intentionally ignored by Git. Create a small deterministic checkpoint for local development:

```powershell
cd KnightPitAI
python -m knightpit_ai train-campaign --minutes 0.1 --games-per-iteration 2 --simulations 2 --max-ply 24 --eval-games 4 --seed 42 --output-dir .campaign-smoke
cd ..
```

### 4. Start the integrated application

```powershell
npm run dev
```

`scripts/dev.mjs` starts the local AI service on `127.0.0.1:8000`, waits for `/health`, and then starts Vite. By default it looks for a checkpoint in `KnightPitAI/.campaign-smoke/`, followed by the documented campaign and checkpoint locations. Set `KNIGHTPIT_CHECKPOINT` to select another `.npz` file explicitly:

```powershell
$env:KNIGHTPIT_CHECKPOINT = "$PWD\KnightPitAI\.campaign-smoke\champion.npz"
npm run dev
```

The frontend uses the AI endpoint configured by `VITE_AI_URL`; the default is `http://127.0.0.1:8000`.

## AI commands

Run these commands from `KnightPitAI` after activating the Python environment:

```powershell
python -m knightpit_ai self-play --games 8 --simulations 4 --max-ply 80 --seed 42 --output data/generated/smoke.jsonl
python -m knightpit_ai train --epochs 2 --batch-size 32 --data data/generated/smoke.jsonl
python -m knightpit_ai evaluate --games 20 --seed 42 --checkpoint checkpoints/knightpit-epoch-0001.npz
python -m knightpit_ai inspect-checkpoint --checkpoint checkpoints/knightpit-epoch-0001.npz
```

The service can also be started directly:

```powershell
$env:KNIGHTPIT_CHECKPOINT = "data/generated/campaign-60m/champion.npz"
python -m knightpit_ai.api
```

The API provides `GET /health` and `POST /predict`. The prediction request accepts `fen`, a UCI move list, and `time_budget_ms`. Invalid positions, illegal histories, terminal positions, and missing checkpoints return explicit HTTP errors.

## Verification

```powershell
cd KnightPitAI
python -m pytest
python tools/check_publication.py
cd ..
npm run build
```

The CI workflow runs the backend tests, a deterministic self-play smoke test, the publication audit, and the frontend production build.

## Licensing and attribution

KnightPit source code, tests, configuration, and project-generated data are released under the MIT License. Third-party packages and assets retain their upstream licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the dependency and asset inventory, and [LICENSE](LICENSE) for the project license.

This project was developed with **GPT-5.6-Luna** using **Oh My Pi** as the coding harness. This disclosure describes the development workflow and does not change the copyright, license, or ownership of the repository contents.

## Scope and limitations

KnightPit is a research and learning prototype, not a competitive chess engine and not an Elo certification. Its CPU-oriented model, shallow configurable search, self-play data, and evaluation suite are intended to demonstrate a complete autonomous chess pipeline while keeping the system reproducible on ordinary hardware.
