import random
import textwrap
from abc import ABC, abstractmethod
from typing import List, Union

import chess
import chess.engine
import outlines
from outlines import models

# https://official-stockfish.github.io/docs/stockfish-wiki/UCI-&-Commands.html
# Supports ELOs from 1320 - 3190 (UCI_LimitStrength must be 'True')

class ChessBoard(chess.Board):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.algebraic_history = []

    # TODO: this should return a color from the chess module; not a string
    def waiting_on(self) -> str:
        return "white" if self.turn else "black"

    def submit_move(self, move: str):
        algebraic_move = self.parse_san(move)
        algebraic = self.san(algebraic_move)
        self.algebraic_history.append(algebraic)

        self.push_san(move)

    def move_history(self) -> str:
        moves = self.algebraic_history

        turn = 0
        white_turn = True
        lines = []
        row = ""

        for move in moves:
            if white_turn:
                turn += 1
                row = f"{turn}. {move}"
                white_turn = False
            else:
                row += f" {move}"
                lines.append(row)
                row = ""
                white_turn = True

        if row:
            lines.append(row)

        return "\n".join(lines)

    def pretty(self) -> str:
    
        pieces = {
            "r": "♜",
            "n": "♞",
            "b": "♝",
            "q": "♛",
            "k": "♚",
            "p": "♟",
            "R": "♖",
            "N": "♘",
            "B": "♗",
            "Q": "♕",
            "K": "♔",
            "P": "♙",
        }
    
        board_rows = []
        board_rows.append("       (black)")
        board_rows.append("")
        board_rows.append("  a b c d e f g h")
        for i, row in enumerate(str(self).splitlines()):
            for piece_name, piece_unicode in pieces.items():
                row = row.replace(piece_name, piece_unicode)
    
            board_rows.append(f"{8-i} {row}")
    
        board_rows.append("")
        board_rows.append("       (white)")
        return "\n".join(board_rows)
    
    def draw(self):
        print(self.pretty())
    
    def get_valid_moves(self, move_type: str = "uci") -> List[str]:
        # 'type' can be uci or san
        moves = list(self.generate_legal_moves())

        if move_type == "san":
            moves = [self.san(move) for move in moves]

        moves = [str(move) for move in moves]
        return moves


class Player(ABC):
    
    @abstractmethod
    def get_move(self, board: ChessBoard) -> str:
        pass


class Random(Player):

    def __init__(self):
        pass

    def get_move(self, board: ChessBoard) -> str:
        legal_moves = board.get_valid_moves()
        return random.choice(legal_moves)


class Stockfish(Player):

    engine = chess.engine.SimpleEngine.popen_uci("engines/stockfish.exe")

    # TODO: add a validator here
    # ELO should only every range from 1320 - 3190
    def __init__(self, elo: int):
        self.elo = elo

    def _set_elo(self):
        self.engine.configure(options={"UCI_LimitStrength": True})
        self.engine.configure(options={"UCI_Elo": self.elo})

    def get_move(self, board: ChessBoard) -> str:
        self._set_elo()
        result = self.engine.play(board, chess.engine.Limit(time=0.1))
        return str(result.move)


class OpenAI(Player):

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = models.openai(model)

    def unstructured_move_prompt(self, board: ChessBoard) -> str:
        prompt = f"""
You are a chess grandmaster evaluating a game.
The game has progressed as follows:

```move_history
{board.move_history()}
```

The board is in the following position:

```current_board
{board.pretty()}
```

{board.waiting_on().lower().capitalize()} to move.

As grandmaster, determine the next best move for {board.waiting_on().lower().capitalize()}.
Be detailed. Think ahead. Explain your reasoning.
"""
        return prompt

    def extract_move_prompt(self, board: ChessBoard, grandmaster_suggestion: str) -> str:
        prompt = f"""
A chess board is in the following state

{board.pretty()}

A grandmaster gave the following analysis:

{grandmaster_suggestion}

Extract the next move the grandmaster suggested.
Respond with only the next move suggested by the grandmaster.
Do not respond with any additional information of any kind

Good answers:

    e5       # valid move in algebraic notation

Bad answers:

    1... e5  # move should not include leading numbers
        """
        return prompt

    def get_move(self, board: ChessBoard) -> str:
        prompt = self.unstructured_move_prompt(board)
        move_suggestion = self.model(prompt)
        print("*"*25)
        print(prompt)
        print(move_suggestion)
        print("*"*25)

        print("*"*25)
        prompt = self.extract_move_prompt(board, move_suggestion)
        move = self.model(prompt)
        print(board.get_valid_moves(move_type="san"))
        print(prompt)
        print(move)

        valid_move = True
        try:
            board.parse_san(move)
        except ValueError:
            valid_move = False

        if valid_move:
            print("MOVE VALID!!")
            print("*"*25)
            return move
        print("*"*25)

        print("*"*25)
        print("FORCING MOVE")
        valid_moves = board.get_valid_moves(move_type="san")
        generator = outlines.generate.choice(self.model, valid_moves)
        move = generator(prompt)
        print("*"*25)
        return move


board = ChessBoard()
board.draw()

white = Stockfish(1320)
#black = Stockfish(1500)
black = OpenAI()

moves = 0
while not board.is_game_over():
    moves += 1
    turn = board.waiting_on()
    move = white.get_move(board) if turn == "white" else black.get_move(board)
    board.submit_move(move)

    print()
    board.draw()
    print()

assert board.is_game_over()
board.draw()

results = {
    "1/2-1/2": "tie",
    "1-0": "white_win",
    "0-1": "black_win"
}
print(board.algebraic_history)
print(board.outcome())
print(board.move_history())

result = board.result()
print(results[result])

Stockfish.engine.close()
