from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .board import ChessEnvironment, IllegalMove, InvalidPosition
from .mcts import MCTS, choose_move
from .model import PolicyValueNetwork


class PredictRequest(BaseModel):
    fen: str
    moves: list[str] = Field(default_factory=list)
    time_budget_ms: int = Field(default=250, ge=1, le=10_000)


class PredictResponse(BaseModel):
    move: str
    evaluation: float
    model_version: str
    legal: bool


def create_app(checkpoint: str | None = None, simulations: int = 16) -> FastAPI:
    app = FastAPI(title="KnightPit AI", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    model_path = checkpoint or os.getenv("KNIGHTPIT_CHECKPOINT")
    model: PolicyValueNetwork | None = None
    if model_path:
        try:
            model = PolicyValueNetwork.load_checkpoint(model_path)
            model.version = Path(model_path).stem
        except (FileNotFoundError, KeyError, ValueError, OSError):
            model = None

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "model_loaded": model is not None, "model_version": model.version if model else None}

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        if model is None:
            raise HTTPException(status_code=503, detail="No model checkpoint loaded")
        try:
            environment = ChessEnvironment.from_fen(request.fen)
            environment.apply_sequence(request.moves)
        except (InvalidPosition, IllegalMove) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if environment.is_terminal():
            raise HTTPException(status_code=409, detail=f"Position is terminal: {environment.status().kind}")
        tree = MCTS(
            model,
            simulations=max(1, min(simulations, request.time_budget_ms // 5 or 1)),
            time_limit_seconds=request.time_budget_ms / 1000.0,
        )
        counts = tree.search(environment.board, time_limit_seconds=request.time_budget_ms / 1000.0)
        if not counts:
            raise HTTPException(status_code=409, detail="Position has no legal moves")
        move = choose_move(counts, temperature=0.0, rng=__import__("random").Random(0))
        prediction = model.predict(environment.board)
        evaluation = prediction.value if environment.board.turn == "white" else -prediction.value
        legal = move in environment.legal_moves()
        if not legal:
            raise HTTPException(status_code=500, detail="Model produced a non-legal move")
        return PredictResponse(move=move, evaluation=float(evaluation), model_version=model.version, legal=True)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("knightpit_ai.api:app", host="127.0.0.1", port=int(os.getenv("KNIGHTPIT_API_PORT", "8000")), reload=False, ws="none")
