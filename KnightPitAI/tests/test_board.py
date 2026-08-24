import pytest

from knightpit_ai.board import BoardState, ChessEnvironment, IllegalMove, InvalidPosition, Move, parse_square, square_name


def test_initial_position_has_twenty_legal_moves():
    environment = ChessEnvironment.initial()
    assert len(environment.legal_moves()) == 20
    assert environment.fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")


def test_square_helpers_and_move_round_trip():
    assert parse_square("a8") == 0
    assert parse_square("h1") == 63
    assert square_name(36) == "e4"
    assert Move.from_uci("a7a8q").uci() == "a7a8q"
    with pytest.raises(ValueError):
        parse_square("i9")

def test_castling_is_legal_after_clearing_path():
    environment = ChessEnvironment.initial()
    environment.apply_sequence(["e2e4", "e7e5", "g1f3", "b8c6", "f1e2", "g8f6", "e1g1"])
    assert environment.board.piece_at(parse_square("g1")).symbol() == "K"
    assert environment.board.piece_at(parse_square("f1")).symbol() == "R"


def test_castling_through_check_is_rejected():
    environment = ChessEnvironment.from_fen("r3k2r/5r2/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert "e1g1" not in environment.legal_moves()


def test_en_passant_is_legal_and_captures_pawn():
    environment = ChessEnvironment.initial()
    environment.apply_sequence(["e2e4", "a7a6", "e4e5", "d7d5"])
    assert "e5d6" in environment.legal_moves()
    environment.apply_uci("e5d6")
    assert environment.board.piece_at(parse_square("d5")) is None
    assert environment.board.piece_at(parse_square("d6")).symbol() == "P"


def test_promotion_is_explicit_and_legal():
    environment = ChessEnvironment.from_fen("7k/P7/8/8/8/8/6K1/8 w - - 0 1")
    assert "a7a8q" in environment.legal_moves()
    environment.apply_uci("a7a8q")
    assert environment.board.piece_at(parse_square("a8")).symbol() == "Q"


def test_fen_round_trip_and_checkmate():
    environment = ChessEnvironment.initial()
    environment.apply_sequence(["f2f3", "e7e5", "g2g4", "d8h4"])
    assert ChessEnvironment.from_fen(environment.fen).fen == environment.fen
    assert environment.status().kind == "checkmate"
    assert environment.status().winner == "black"
    assert environment.is_terminal()


def test_stalemate_is_terminal_draw():
    environment = ChessEnvironment.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert environment.status().kind == "stalemate"
    assert environment.legal_moves() == []


def test_insufficient_material_is_terminal():
    environment = ChessEnvironment.from_fen("7k/8/8/8/8/8/6K1/8 w - - 0 1")
    assert environment.status().kind == "draw-insufficient-material"


def test_repetition_and_move_thresholds():
    environment = ChessEnvironment.initial()
    for _ in range(4):
        environment.apply_sequence(["g1f3", "g8f6", "f3g1", "f6g8"])
    assert environment.board.is_threefold_repetition()
    assert environment.board.is_fivefold_repetition()
    assert environment.status().kind == "draw-fivefold-repetition"
    fifty = ChessEnvironment.from_fen("4k3/8/8/8/8/8/8/R3K3 w - - 100 1")
    assert fifty.status().kind == "draw-fifty-move"
    seventyfive = ChessEnvironment.from_fen("4k3/8/8/8/8/8/8/R3K3 w - - 150 1")
    assert seventyfive.status().kind == "draw-seventyfive-move"

def test_invalid_fen_and_illegal_move_are_rejected():
    with pytest.raises(InvalidPosition):
        ChessEnvironment.from_fen("not a fen")
    environment = ChessEnvironment.initial()
    with pytest.raises(IllegalMove):
        environment.apply_uci("e2e5")


def test_board_state_push_is_immutable():
    board = BoardState.initial()
    next_board = board.push(Move.from_uci("e2e4"))
    assert board.turn == "white"
    assert next_board.turn == "black"
    assert board.piece_at(parse_square("e2")).symbol() == "P"
