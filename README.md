# KnightPit

KnightPit is an educational, open-source chess application that combines a React/TypeScript interface with a small chess AI written in Python. The project is designed to run on CPU-only hardware and to make the complete training and inference pipeline reproducible and inspectable.

The AI is developed from scratch around a project-owned chess environment, a compact NumPy policy/value network, CPU MCTS with PUCT, and self-play training. A local FastAPI service exposes model inference to the frontend. The browser client sends FEN positions and UCI move history, then validates every response against its own legal-move engine before changing the local game state.

## Features

- Play against KnightPit AI from the web interface.
- Review completed games with each mover's remaining clock time after increment; older games without recorded times show `—`.
- Project-owned chess rules with legal-move validation, castling, en passant, promotion, checkmate, stalemate, and draw handling.
- CPU-only self-play, replay generation, training, evaluation, checkpoint inspection, and resumable campaigns.
- Local FastAPI endpoints for health checks and move prediction.
- Training and evaluation metadata with deterministic seeds, model versions, reward profiles, and campaign metrics.
- No Stockfish, external chess engine, tablebase, or unverified game dataset.

## Technology

- **Frontend:** React, TypeScript, React Router, Motion, Tailwind CSS, and Vite.
- **AI service:** Python 3.10–3.13, NumPy, FastAPI, and Uvicorn.
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

- Node.js **22.12+** (recommended), or 20.19+.
- Python **3.10–3.13**, with `venv` and `pip`, available as `python3`, `python`, or the Windows `py` launcher. The CPU lockfile uses NumPy 2.2.6; Python 3.14 is not supported by its wheels.
- Windows x64, macOS, or Linux with compatible Python wheels; no compiler, CUDA, or GPU required.
- Internet access for the first dependency installation. Later starts reuse the Python environment, checkpoint, and pip cache.

On Windows, install prerequisites with `winget install --exact --id OpenJS.NodeJS.LTS` and `winget install --exact --id Python.Python.3.13`, then open a new terminal. On Debian/Ubuntu, install Python's environment support with `sudo apt-get install python3 python3-venv python3-pip`; on macOS, `brew install node python@3.13`.


## Quick start

From the repository root, in PowerShell, cmd, or a POSIX shell:

```sh
npm install
npm run dev
```

Open **http://127.0.0.1:5173**, choose **Play**, then **Start game**. You play White; the model replies as Black. Stop both services with **Ctrl+C**.

`npm run dev` automatically:

1. Reuses a Python environment with the exact locked runtime packages, preferring `KnightPitAI/.venv` and then an activated environment. Otherwise it creates/repairs `KnightPitAI/.venv` and installs `requirements-cpu.lock` with hash verification and binary wheels. No activation or global package installation is needed.
2. Reuses a checkpoint from `.campaign-smoke`, the existing `data/generated/campaign-60m` locations, or `checkpoints/knightpit-epoch-0001.npz`, in the launcher's existing order.
3. If none exists, creates `KnightPitAI/checkpoints/development-seed-42.npz` using the project-owned network and fixed seed **42**. This is a small **untrained development model**, not a trained opponent or a strength claim. No campaign, external engine, dataset, or downloaded model is required.
4. Starts the API at **http://127.0.0.1:8000**, requires `/health` to report `model_loaded: true`, then starts Vite on port **5173**. A busy frontend port fails instead of silently moving to an origin the API does not allow.

Generated checkpoints, replays, environments, and caches remain ignored by Git. Existing checkpoints are validated, never silently replaced. Subsequent starts skip dependency installation when locked versions still match and do not regenerate the checkpoint. Pip retains its normal download cache.

To prepare the local backend without starting either server:

```sh
npm run bootstrap
```

### Advanced overrides

`KNIGHTPIT_CHECKPOINT` selects an existing `.npz` file; relative paths resolve from the repository root. A missing or invalid explicit checkpoint fails rather than silently selecting another model.

```powershell
$env:KNIGHTPIT_CHECKPOINT = "$PWD\KnightPitAI\data\generated\campaign-60m\champion.npz"
npm run dev
```

`VITE_AI_URL` selects an already-running API and **skips all local Python/checkpoint setup**. It is read from the shell or Vite's `.env`/`.env.local`/`.env.development` files, with Vite's usual precedence. The configured service must expose `/health` with a loaded model, `/predict`, and allow the frontend origin through CORS.

```powershell
$env:VITE_AI_URL = "http://127.0.0.1:9000"
npm run dev
```

POSIX equivalents: `KNIGHTPIT_CHECKPOINT=/path/model.npz npm run dev` or `VITE_AI_URL=http://127.0.0.1:9000 npm run dev`. For a local API on another port, set `KNIGHTPIT_API_PORT`; the integrated launcher configures the frontend to match unless `VITE_AI_URL` is set. `npm run dev:frontend` starts only Vite without backend checks.

### Bootstrap recovery

Failures print the failed operation and an exact command to run **from the repository root**. Keep the preceding pip/API error when reporting a failure.

- **Python missing/unsupported:** install a supported Python using the prerequisite command above, reopen the terminal, then `npm run dev`.
- **Missing `venv` on Debian/Ubuntu:** `sudo apt-get install python3-venv`, then `npm run dev`.
- **Dependency download/hash failure:** correct the network/index problem and run the printed `.venv` Python `-m pip install --require-hashes --only-binary=:all: -r ...` command. Do not disable hash verification. Then `npm run dev`.
- **Missing/invalid explicit checkpoint:** correct the path or run `Remove-Item Env:KNIGHTPIT_CHECKPOINT -ErrorAction SilentlyContinue` in PowerShell (`unset KNIGHTPIT_CHECKPOINT` on POSIX), then `npm run dev`. For an invalid automatically selected checkpoint, the error prints a command to move it aside without deleting it.
- **Occupied API/frontend port:** stop the other process using that port, then `npm run dev`. To change only the local API port in PowerShell: `$env:KNIGHTPIT_API_PORT = "8001"; npm run dev`.

For backend development, activate the prepared environment and install test dependencies:

```powershell
KnightPitAI\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r KnightPitAI/requirements-test.lock
```

On POSIX, activate with `. KnightPitAI/.venv/bin/activate`. If bootstrap reused an already-active environment, continue using that environment instead.

## AI commands

Run these commands from `KnightPitAI` after activating the Python environment:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m knightpit_ai self-play --games 8 --simulations 4 --max-ply 80 --seed 42 --output data/generated/smoke.jsonl
python -m knightpit_ai train --epochs 2 --batch-size 32 --data data/generated/smoke.jsonl
python -m knightpit_ai evaluate --games 20 --seed 42 --checkpoint checkpoints/knightpit-epoch-0001.npz
python -m knightpit_ai inspect-checkpoint --checkpoint checkpoints/knightpit-epoch-0001.npz
```

On POSIX, use `export PYTHONPATH="$PWD/src"` instead of the PowerShell assignment. The integrated launcher sets this path automatically.

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

The CI workflow runs the backend tests, deterministic self-play, the publication audit, and the frontend production build. A separate Ubuntu/Windows startup job runs `npm ci` and `npm run test:startup` against an isolated source checkout without local environments, checkpoints, or `.env` files. It exercises automatic installation, loaded health, legal inference, offline reuse, deterministic checkpoint generation, failure recovery, and overrides.

## Licensing and attribution

KnightPit source code, tests, configuration, and project-generated data are released under the MIT License. Third-party packages and assets retain their upstream licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the dependency and asset inventory, and [LICENSE](LICENSE) for the project license.

This project was developed with **GPT-5.6-Luna** using **Oh My Pi** as the coding harness. This disclosure describes the development workflow and does not change the copyright, license, or ownership of the repository contents.

## Scope and limitations

KnightPit is a research and learning prototype, not a competitive chess engine and not an Elo certification. Its CPU-oriented model, shallow configurable search, self-play data, and evaluation suite are intended to demonstrate a complete autonomous chess pipeline while keeping the system reproducible on ordinary hardware.
