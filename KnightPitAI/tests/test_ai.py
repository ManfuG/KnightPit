import json
import numpy as np
from fastapi.testclient import TestClient

from knightpit_ai.api import create_app
from knightpit_ai.board import ChessEnvironment, Move
from knightpit_ai.encoding import ENCODING_SHAPE, MOVE_SPACE_SIZE, encode_board, index_to_move, move_to_index
from knightpit_ai.model import PolicyValueNetwork
from knightpit_ai.self_play import SelfPlayConfig, generate_self_play
from knightpit_ai.train import TrainingConfig, train_network


def test_encoding_and_move_space_are_stable():
    board = ChessEnvironment.initial().board
    encoded = encode_board(board)
    assert encoded.shape == ENCODING_SHAPE
    assert encoded.dtype == np.float32
    assert MOVE_SPACE_SIZE == 20480
    move = Move.from_uci("e2e4")
    assert index_to_move(move_to_index(move)) == move


def test_self_play_only_records_legal_moves_and_is_seed_reproducible():
    config = SelfPlayConfig(games=2, simulations=2, max_ply=12, seed=7)
    first, first_stats = generate_self_play(PolicyValueNetwork(seed=7), config)
    second, second_stats = generate_self_play(PolicyValueNetwork(seed=7), config)
    assert first_stats.legal_move_rate == 1.0
    assert first_stats.completed == 2
    assert first_stats.plies == second_stats.plies
    assert len(first) == len(second)
    assert first._items[0].policy == second._items[0].policy


def test_checkpoint_round_trip(tmp_path):
    path = tmp_path / "model.npz"
    original = PolicyValueNetwork(seed=11)
    original.version = "test"
    original.save_checkpoint(path)
    loaded = PolicyValueNetwork.load_checkpoint(path)
    assert loaded.version == "test"
    assert loaded.hidden_size == original.hidden_size
    assert np.array_equal(loaded.features_w, original.features_w)

def test_training_checkpoints_carry_reward_metadata(tmp_path):
    replay, _ = generate_self_play(
        PolicyValueNetwork(seed=5),
        SelfPlayConfig(games=1, simulations=1, max_ply=2, seed=5),
    )
    network = PolicyValueNetwork(seed=5)
    train_network(
        network,
        replay,
        TrainingConfig(
            epochs=1,
            batch_size=2,
            seed=5,
            reward_profile="principles-v1",
            reward_schedule_version="principles-v1-schedule-1",
        ),
        tmp_path,
    )
    checkpoint = np.load(tmp_path / "knightpit-iteration-0001-epoch-0001.npz", allow_pickle=False)
    metadata = json.loads(str(checkpoint["metadata"]))
    assert metadata["reward_profile"] == "principles-v1"
    assert metadata["reward_schedule_version"] == "principles-v1-schedule-1"


def test_api_health_predict_and_rejections(tmp_path):
    path = tmp_path / "model.npz"
    PolicyValueNetwork(seed=3).save_checkpoint(path)
    client = TestClient(create_app(str(path), simulations=1))
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["model_loaded"] is True
    initial_fen = ChessEnvironment.initial().fen
    prediction = client.post("/predict", json={"fen": initial_fen, "moves": [], "time_budget_ms": 50})
    assert prediction.status_code == 200
    predicted_move = prediction.json()["move"]
    assert prediction.json()["legal"] is True
    assert predicted_move in ChessEnvironment.initial().legal_moves()
    assert client.post("/predict", json={"fen": "invalid", "moves": []}).status_code == 400
    terminal = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    assert client.post("/predict", json={"fen": terminal, "moves": []}).status_code == 409
    illegal = client.post("/predict", json={"fen": initial_fen, "moves": ["e2e5"]})
    assert illegal.status_code == 400


def test_api_requires_loaded_model():
    client = TestClient(create_app(None, simulations=1))
    assert client.get("/health").json()["model_loaded"] is False
    assert client.post("/predict", json={"fen": ChessEnvironment.initial().fen}).status_code == 503
