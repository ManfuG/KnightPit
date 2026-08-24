"""Project-owned chess rules and environment.

The board uses canonical squares: ``0`` is ``a8`` and ``63`` is ``h1``.
No external chess implementation or engine data is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

Color = Literal["white", "black"]
PieceKind = Literal["pawn", "knight", "bishop", "rook", "queen", "king"]
CastleSide = Literal["kingside", "queenside"]

_FILES = "abcdefgh"
_PIECE_KINDS: tuple[PieceKind, ...] = ("pawn", "knight", "bishop", "rook", "queen", "king")
_PROMOTIONS: tuple[PieceKind, ...] = ("queen", "rook", "bishop", "knight")
_PIECE_CHARS: dict[tuple[Color, PieceKind], str] = {
    ("white", "pawn"): "P", ("white", "knight"): "N", ("white", "bishop"): "B",
    ("white", "rook"): "R", ("white", "queen"): "Q", ("white", "king"): "K",
    ("black", "pawn"): "p", ("black", "knight"): "n", ("black", "bishop"): "b",
    ("black", "rook"): "r", ("black", "queen"): "q", ("black", "king"): "k",
}
_CHAR_TO_PIECE: dict[str, Piece] = {}


class InvalidPosition(ValueError):
    """Raised when a FEN does not describe a valid position."""


class IllegalMove(ValueError):
    """Raised when a requested move is not legal in the current position."""


@dataclass(frozen=True)
class Piece:
    color: Color
    kind: PieceKind

    def symbol(self) -> str:
        return _PIECE_CHARS[(self.color, self.kind)]


for _color in ("white", "black"):
    for _kind in _PIECE_KINDS:
        _CHAR_TO_PIECE[_PIECE_CHARS[(_color, _kind)]] = Piece(_color, _kind)


def parse_square(name: str) -> int:
    if not isinstance(name, str) or len(name) != 2 or name[0] not in _FILES or name[1] not in "12345678":
        raise ValueError(f"Invalid square: {name}")
    return (8 - int(name[1])) * 8 + _FILES.index(name[0])


def square_name(square: int) -> str:
    if not isinstance(square, int) or isinstance(square, bool) or not 0 <= square < 64:
        raise ValueError(f"Invalid square index: {square}")
    return f"{_FILES[square % 8]}{8 - square // 8}"


@dataclass(frozen=True)
class Move:
    from_square: int
    to_square: int
    promotion: PieceKind | None = None
    is_castle: CastleSide | None = None
    is_en_passant: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.from_square < 64 or not 0 <= self.to_square < 64 or self.from_square == self.to_square:
            raise ValueError("Move squares must be distinct indices from 0 to 63")
        if self.promotion not in (None, *_PROMOTIONS):
            raise ValueError("Promotion must be queen, rook, bishop, or knight")

    def uci(self) -> str:
        promotion_code = {"queen": "q", "rook": "r", "bishop": "b", "knight": "n"}
        return f"{square_name(self.from_square)}{square_name(self.to_square)}{promotion_code.get(self.promotion, '')}"

    @classmethod
    def from_uci(cls, uci: str) -> "Move":
        if not isinstance(uci, str) or len(uci) not in (4, 5):
            raise ValueError(f"Invalid UCI move: {uci}")
        try:
            from_square = parse_square(uci[:2])
            to_square = parse_square(uci[2:4])
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move: {uci}") from exc
        promotion: PieceKind | None = None
        if len(uci) == 5:
            promotion = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}.get(uci[4].lower())  # type: ignore[assignment]
            if promotion is None or uci[4] != uci[4].lower():
                raise ValueError(f"Invalid UCI move: {uci}")
        return cls(from_square, to_square, promotion)


@dataclass(frozen=True)
class BoardState:
    squares: tuple[Piece | None, ...]
    turn: Color = "white"
    white_kingside: bool = True
    white_queenside: bool = True
    black_kingside: bool = True
    black_queenside: bool = True
    ep_square: int | None = None
    halfmove_clock: int = 0
    fullmove_number: int = 1
    repetition_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.squares) != 64:
            raise InvalidPosition("Board must contain exactly 64 squares")
        if self.turn not in ("white", "black"):
            raise InvalidPosition("Invalid side to move")
        if self.ep_square is not None and not 0 <= self.ep_square < 64:
            raise InvalidPosition("Invalid en-passant square")
        if self.halfmove_clock < 0 or self.fullmove_number < 1:
            raise InvalidPosition("Invalid FEN counters")
        if not self.repetition_keys:
            object.__setattr__(self, "repetition_keys", (self._position_key(),))

    @classmethod
    def initial(cls) -> "BoardState":
        squares: list[Piece | None] = [None] * 64
        back: tuple[PieceKind, ...] = ("rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook")
        for file, kind in enumerate(back):
            squares[file] = Piece("black", kind)
            squares[8 + file] = Piece("black", "pawn")
            squares[48 + file] = Piece("white", "pawn")
            squares[56 + file] = Piece("white", kind)
        return cls(tuple(squares))

    @classmethod
    def from_fen(cls, fen: str) -> "BoardState":
        fields = fen.split()
        if len(fields) != 6:
            raise InvalidPosition("FEN must contain six fields")
        placement, turn, castling, ep, halfmove, fullmove = fields
        rows = placement.split("/")
        if len(rows) != 8:
            raise InvalidPosition("FEN board must contain eight ranks")
        squares: list[Piece | None] = []
        for row in rows:
            count = 0
            for char in row:
                if char in _CHAR_TO_PIECE:
                    squares.append(_CHAR_TO_PIECE[char])
                    count += 1
                elif char in "12345678":
                    squares.extend([None] * int(char))
                    count += int(char)
                else:
                    raise InvalidPosition(f"Invalid FEN piece: {char}")
            if count != 8:
                raise InvalidPosition("FEN rank does not contain eight squares")
        if turn not in ("w", "b"):
            raise InvalidPosition("Invalid FEN side to move")
        if castling == "-":
            rights = set()
        elif castling and all(char in "KQkq" for char in castling) and len(set(castling)) == len(castling):
            rights = set(castling)
        else:
            raise InvalidPosition("Invalid FEN castling rights")
        if ep == "-":
            ep_square = None
        else:
            try:
                ep_square = parse_square(ep)
            except ValueError as exc:
                raise InvalidPosition("Invalid FEN en-passant square") from exc
            expected_rank = 5 if turn == "b" else 2
            if ep_square // 8 != expected_rank:
                raise InvalidPosition("Invalid FEN en-passant rank")
        try:
            halfmove_value = int(halfmove)
            fullmove_value = int(fullmove)
        except ValueError as exc:
            raise InvalidPosition("Invalid FEN move counters") from exc
        board = cls(tuple(squares), "white" if turn == "w" else "black", "K" in rights, "Q" in rights, "k" in rights, "q" in rights, ep_square, halfmove_value, fullmove_value)
        if not board.is_valid():
            raise InvalidPosition("FEN position is not legal")
        return board

    def piece_at(self, square: int) -> Piece | None:
        if not isinstance(square, int) or isinstance(square, bool) or not 0 <= square < 64:
            raise ValueError(f"Invalid square index: {square}")
        return self.squares[square]

    def piece_map(self) -> dict[int, Piece]:
        return {square: piece for square, piece in enumerate(self.squares) if piece is not None}

    def _castling_field(self) -> str:
        value = "".join(char for flag, char in ((self.white_kingside, "K"), (self.white_queenside, "Q"), (self.black_kingside, "k"), (self.black_queenside, "q")) if flag)
        return value or "-"

    def fen(self) -> str:
        rows: list[str] = []
        for rank in range(8):
            row = ""
            empty = 0
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                if piece is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece.symbol()
            if empty:
                row += str(empty)
            rows.append(row)
        ep = square_name(self.ep_square) if self.ep_square is not None else "-"
        return f"{'/'.join(rows)} {'w' if self.turn == 'white' else 'b'} {self._castling_field()} {ep} {self.halfmove_clock} {self.fullmove_number}"

    def _position_key(self) -> str:
        return " ".join(self.fen().split()[:4])

    def _king_square(self, color: Color) -> int | None:
        return next((square for square, piece in enumerate(self.squares) if piece == Piece(color, "king")), None)

    @staticmethod
    def _opponent(color: Color) -> Color:
        return "black" if color == "white" else "white"

    def _attacked(self, square: int, by_color: Color) -> bool:
        rank, file = divmod(square, 8)
        pawn_rank = rank + (1 if by_color == "white" else -1)
        if 0 <= pawn_rank < 8:
            for pawn_file in (file - 1, file + 1):
                if 0 <= pawn_file < 8 and self.squares[pawn_rank * 8 + pawn_file] == Piece(by_color, "pawn"):
                    return True
        for dr, df in ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)):
            r, f = rank + dr, file + df
            if 0 <= r < 8 and 0 <= f < 8 and self.squares[r * 8 + f] == Piece(by_color, "knight"):
                return True
        for dr, df, kinds in ((-1, 0, ("rook", "queen")), (1, 0, ("rook", "queen")), (0, -1, ("rook", "queen")), (0, 1, ("rook", "queen")), (-1, -1, ("bishop", "queen")), (-1, 1, ("bishop", "queen")), (1, -1, ("bishop", "queen")), (1, 1, ("bishop", "queen"))):
            r, f = rank + dr, file + df
            while 0 <= r < 8 and 0 <= f < 8:
                piece = self.squares[r * 8 + f]
                if piece is not None:
                    if piece.color == by_color and piece.kind in kinds:
                        return True
                    break
                r += dr
                f += df
        for dr in (-1, 0, 1):
            for df in (-1, 0, 1):
                if not dr and not df:
                    continue
                r, f = rank + dr, file + df
                if 0 <= r < 8 and 0 <= f < 8 and self.squares[r * 8 + f] == Piece(by_color, "king"):
                    return True
        return False

    def _pseudo_moves(self) -> list[Move]:
        moves: list[Move] = []
        opponent = self._opponent(self.turn)
        for square, piece in enumerate(self.squares):
            if piece is None or piece.color != self.turn:
                continue
            rank, file = divmod(square, 8)
            if piece.kind == "pawn":
                direction = -1 if self.turn == "white" else 1
                start_rank = 6 if self.turn == "white" else 1
                promotion_rank = 0 if self.turn == "white" else 7
                next_rank = rank + direction
                if 0 <= next_rank < 8:
                    destination = next_rank * 8 + file
                    if self.squares[destination] is None:
                        if next_rank == promotion_rank:
                            moves.extend(Move(square, destination, promotion=kind) for kind in _PROMOTIONS)
                        else:
                            moves.append(Move(square, destination))
                        if rank == start_rank:
                            jump = (rank + 2 * direction) * 8 + file
                            if self.squares[jump] is None:
                                moves.append(Move(square, jump))
                    for target_file in (file - 1, file + 1):
                        if not 0 <= target_file < 8:
                            continue
                        target = next_rank * 8 + target_file
                        target_piece = self.squares[target]
                        is_ep = target == self.ep_square and target_piece is None
                        if (target_piece is not None and target_piece.color == opponent and target_piece.kind != "king") or (is_ep and self.squares[target - 8 * direction] == Piece(opponent, "pawn")):
                            if next_rank == promotion_rank:
                                moves.extend(Move(square, target, promotion=kind, is_en_passant=is_ep) for kind in _PROMOTIONS)
                            else:
                                moves.append(Move(square, target, is_en_passant=is_ep))
            elif piece.kind == "knight":
                for dr, df in ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)):
                    r, f = rank + dr, file + df
                    if 0 <= r < 8 and 0 <= f < 8 and (self.squares[r * 8 + f] is None or (self.squares[r * 8 + f].color == opponent and self.squares[r * 8 + f].kind != "king")):
                        moves.append(Move(square, r * 8 + f))
            elif piece.kind in ("bishop", "rook", "queen"):
                directions = []
                if piece.kind in ("bishop", "queen"):
                    directions.extend(((-1, -1), (-1, 1), (1, -1), (1, 1)))
                if piece.kind in ("rook", "queen"):
                    directions.extend(((-1, 0), (1, 0), (0, -1), (0, 1)))
                for dr, df in directions:
                    r, f = rank + dr, file + df
                    while 0 <= r < 8 and 0 <= f < 8:
                        target = self.squares[r * 8 + f]
                        if target is None:
                            moves.append(Move(square, r * 8 + f))
                        else:
                            if target.color == opponent and target.kind != "king":
                                moves.append(Move(square, r * 8 + f))
                            break
                        r += dr
                        f += df
            else:
                for dr in (-1, 0, 1):
                    for df in (-1, 0, 1):
                        if not dr and not df:
                            continue
                        r, f = rank + dr, file + df
                        if 0 <= r < 8 and 0 <= f < 8 and (self.squares[r * 8 + f] is None or (self.squares[r * 8 + f].color == opponent and self.squares[r * 8 + f].kind != "king")):
                            moves.append(Move(square, r * 8 + f))
                if not self.is_check():
                    if self.turn == "white" and square == 60:
                        if self.white_kingside and self.squares[61] is None and self.squares[62] is None and self.squares[63] == Piece("white", "rook") and not self._attacked(61, opponent) and not self._attacked(62, opponent):
                            moves.append(Move(60, 62, is_castle="kingside"))
                        if self.white_queenside and self.squares[59] is None and self.squares[58] is None and self.squares[57] is None and self.squares[56] == Piece("white", "rook") and not self._attacked(59, opponent) and not self._attacked(58, opponent):
                            moves.append(Move(60, 58, is_castle="queenside"))
                    elif self.turn == "black" and square == 4:
                        if self.black_kingside and self.squares[5] is None and self.squares[6] is None and self.squares[7] == Piece("black", "rook") and not self._attacked(5, opponent) and not self._attacked(6, opponent):
                            moves.append(Move(4, 6, is_castle="kingside"))
                        if self.black_queenside and self.squares[3] is None and self.squares[2] is None and self.squares[1] is None and self.squares[0] == Piece("black", "rook") and not self._attacked(3, opponent) and not self._attacked(2, opponent):
                            moves.append(Move(4, 2, is_castle="queenside"))
        return moves

    def legal_moves(self) -> list[Move]:
        legal: list[Move] = []
        for move in self._pseudo_moves():
            next_board = self._push_unchecked(move)
            king = next_board._king_square(self.turn)
            if king is not None and not next_board._attacked(king, self._opponent(self.turn)):
                legal.append(move)
        return legal

    def _push_unchecked(self, move: Move) -> "BoardState":
        piece = self.squares[move.from_square]
        if piece is None:
            raise IllegalMove(f"No piece on {square_name(move.from_square)}")
        squares = list(self.squares)
        captured = squares[move.to_square]
        squares[move.from_square] = None
        if move.is_en_passant:
            captured_square = move.to_square - 8 * (-1 if piece.color == "white" else 1)
            captured = squares[captured_square]
            squares[captured_square] = None
        placed = Piece(piece.color, move.promotion) if move.promotion else piece
        squares[move.to_square] = placed
        wk, wq, bk, bq = self.white_kingside, self.white_queenside, self.black_kingside, self.black_queenside
        if piece.kind == "king":
            if piece.color == "white":
                wk = wq = False
            else:
                bk = bq = False
            if move.is_castle == "kingside":
                rook_from, rook_to = (63, 61) if piece.color == "white" else (7, 5)
                squares[rook_to] = squares[rook_from]
                squares[rook_from] = None
            elif move.is_castle == "queenside":
                rook_from, rook_to = (56, 59) if piece.color == "white" else (0, 3)
                squares[rook_to] = squares[rook_from]
                squares[rook_from] = None
        if piece.kind == "rook":
            if move.from_square == 63: wk = False
            if move.from_square == 56: wq = False
            if move.from_square == 7: bk = False
            if move.from_square == 0: bq = False
        if captured == Piece("white", "rook"):
            if move.to_square == 63: wk = False
            if move.to_square == 56: wq = False
        if captured == Piece("black", "rook"):
            if move.to_square == 7: bk = False
            if move.to_square == 0: bq = False
        ep_square = None
        if piece.kind == "pawn" and abs(move.to_square - move.from_square) == 16:
            ep_square = (move.to_square + move.from_square) // 2
        next_state = BoardState(tuple(squares), self._opponent(self.turn), wk, wq, bk, bq, ep_square, 0 if piece.kind == "pawn" or captured is not None or move.is_en_passant else self.halfmove_clock + 1, self.fullmove_number + (1 if self.turn == "black" else 0), self.repetition_keys)
        object.__setattr__(next_state, "repetition_keys", self.repetition_keys + (next_state._position_key(),))
        return next_state

    def push(self, move: Move) -> "BoardState":
        for legal in self.legal_moves():
            if legal.from_square == move.from_square and legal.to_square == move.to_square and legal.promotion == move.promotion:
                return self._push_unchecked(legal)
        raise IllegalMove(f"Illegal move {move.uci()} in {self.fen()}")

    def is_check(self) -> bool:
        king = self._king_square(self.turn)
        return king is not None and self._attacked(king, self._opponent(self.turn))

    def is_checkmate(self) -> bool:
        return self.is_check() and not self.legal_moves()

    def is_stalemate(self) -> bool:
        return not self.is_check() and not self.legal_moves()

    def is_insufficient_material(self) -> bool:
        pieces = [piece for piece in self.squares if piece is not None and piece.kind != "king"]
        if not pieces:
            return True
        if any(piece.kind in ("pawn", "rook", "queen") for piece in pieces):
            return False
        if len(pieces) == 1:
            return pieces[0].kind in ("bishop", "knight")
        if all(piece.kind == "bishop" for piece in pieces):
            bishop_colors = {((square // 8) + (square % 8)) % 2 for square, piece in enumerate(self.squares) if piece is not None and piece.kind == "bishop"}
            return len(bishop_colors) == 1
        return False

    def is_threefold_repetition(self) -> bool:
        key = self._position_key()
        return self.repetition_keys.count(key) >= 3

    def is_fivefold_repetition(self) -> bool:
        key = self._position_key()
        return self.repetition_keys.count(key) >= 5

    def is_fifty_moves(self) -> bool:
        return self.halfmove_clock >= 100

    def is_seventyfive_moves(self) -> bool:
        return self.halfmove_clock >= 150

    def is_valid(self) -> bool:
        white_kings = [square for square, piece in enumerate(self.squares) if piece == Piece("white", "king")]
        black_kings = [square for square, piece in enumerate(self.squares) if piece == Piece("black", "king")]
        if len(white_kings) != 1 or len(black_kings) != 1:
            return False
        if any(piece is not None and piece.kind == "pawn" and square // 8 in (0, 7) for square, piece in enumerate(self.squares)):
            return False
        if self.white_kingside and (self.squares[60] != Piece("white", "king") or self.squares[63] != Piece("white", "rook")):
            return False
        if self.white_queenside and (self.squares[60] != Piece("white", "king") or self.squares[56] != Piece("white", "rook")):
            return False
        if self.black_kingside and (self.squares[4] != Piece("black", "king") or self.squares[7] != Piece("black", "rook")):
            return False
        if self.black_queenside and (self.squares[4] != Piece("black", "king") or self.squares[0] != Piece("black", "rook")):
            return False
        if self.ep_square is not None:
            expected_rank = 5 if self.turn == "black" else 2
            pawn_square = self.ep_square - 8 if self.turn == "black" else self.ep_square + 8
            expected_pawn = Piece("white", "pawn") if self.turn == "black" else Piece("black", "pawn")
            if self.ep_square // 8 != expected_rank or self.squares[self.ep_square] is not None or not 0 <= pawn_square < 64 or self.squares[pawn_square] != expected_pawn:
                return False
        wr, wf = divmod(white_kings[0], 8)
        br, bf = divmod(black_kings[0], 8)
        if max(abs(wr - br), abs(wf - bf)) <= 1:
            return False
        if self._attacked(white_kings[0], "black") and self._attacked(black_kings[0], "white"):
            return False
        return True


@dataclass(frozen=True)
class GameStatus:
    kind: str
    winner: Color | None = None


class ChessEnvironment:
    """Mutable API wrapper around an immutable :class:`BoardState`."""

    def __init__(self, board: BoardState | None = None) -> None:
        self.board = board or BoardState.initial()

    @classmethod
    def initial(cls) -> "ChessEnvironment":
        return cls(BoardState.initial())

    @classmethod
    def from_fen(cls, fen: str) -> "ChessEnvironment":
        return cls(BoardState.from_fen(fen))

    def clone(self) -> "ChessEnvironment":
        return ChessEnvironment(self.board)

    @property
    def fen(self) -> str:
        return self.board.fen()

    @property
    def turn(self) -> Color:
        return self.board.turn

    def legal_moves(self) -> list[str]:
        return [move.uci() for move in self.board.legal_moves()]

    def legal_move_objects(self) -> list[Move]:
        return self.board.legal_moves()

    def apply_uci(self, uci: str) -> None:
        try:
            move = Move.from_uci(uci)
        except ValueError as exc:
            raise IllegalMove(f"Invalid UCI move: {uci}") from exc
        self.push(move)

    def push(self, move: Move) -> None:
        self.board = self.board.push(move)

    def status(self) -> GameStatus:
        if self.board.is_checkmate():
            return GameStatus("checkmate", "black" if self.board.turn == "white" else "white")
        if self.board.is_stalemate():
            return GameStatus("stalemate")
        if self.board.is_insufficient_material():
            return GameStatus("draw-insufficient-material")
        if self.board.is_fivefold_repetition():
            return GameStatus("draw-fivefold-repetition")
        if self.board.is_seventyfive_moves():
            return GameStatus("draw-seventyfive-move")
        if self.board.is_fifty_moves():
            return GameStatus("draw-fifty-move")
        if self.board.is_check():
            return GameStatus("check")
        return GameStatus("playing")

    def is_terminal(self) -> bool:
        return self.status().kind not in {"playing", "check"}

    def result_white_perspective(self) -> float:
        status = self.status()
        if status.winner == "white":
            return 1.0
        if status.winner == "black":
            return -1.0
        return 0.0

    def apply_sequence(self, moves: Iterable[str]) -> None:
        for move in moves:
            self.apply_uci(move)


def parse_fen(fen: str) -> ChessEnvironment:
    return ChessEnvironment.from_fen(fen)


def initial_fen() -> str:
    return ChessEnvironment.initial().fen
