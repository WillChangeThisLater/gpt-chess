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

    def get_move_history(self) -> List[str]:
        moves = self.move_stack
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
        legal_moves = get_possible_moves(board)
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

    def _determine_strategy(self, board: chess.Board) -> str:
        pass

    def get_move(self, board: ChessBoard) -> str:
        valid_moves = get_possible_moves(board)
        generator = outlines.generate.choice(self.model, valid_moves)
        prompt = f"""
You are a chess grandmaster playing in the world chess championship.
The game has progressed as follows:

```move_history
{board.get_move_history()}
```

And now the board is in the following position:

```current_board
{prettify_board(board)}
```

{board.waiting_on().upper()} to move.

Determine the next best move. Return only the next best
move; no explanation of any kind. Use UCI notation.
        """
        move = generator(prompt)
        print(f"openai move is {move}")
        return move


def ai_move(board: chess.Board, model: str = "gpt-4o-mini") -> str:
    model = models.openai(model)
    raw_prompt = textwrap.dedent(f"""
You are a chess grandmaster playing in the world chess championship.
The game has progressed as follows:

```move_history
{get_move_history(board)}
```

And now the board is in the following position:

```current_board
{prettify_board(board)}
```

{waiting_on(board).upper()} to move.

Determine the best line. Think as many steps ahead as
you can. Explain your reasoning. Use UCI notation.
""")

    next_move_explanation = model(raw_prompt)
    choice_prompt = f"""
You are transcribing a chess sequence. The game thus far is as follows:

{get_move_history(board)}

Your job is to extract the next move in the game from a text
summary, which is below. Provide this move in UCI notation.
Do not provide explanations of any kind. Do not provide multiple moves

Example 1 (Good):

    Explanation:

        Thus far the game has progressed as follows:

        1. Nf3 Nf6 2. c4 g6 3. Nc3 Bg7 4. d4 O-O 5. Bf4 d5 6. Qb3 dxc4
        7. Qxc4 c6 8. e4 Nbd7 9. Rd1 Nb6 10. Qc5 Bg4 11. Bg5 Na4 12. Qa3
        Nxc3 13. bxc3 Nxe4 14. Bxe7 Qb6 15. Bc4 Nxc3 16. Bc5 Rfe8+ 17. Kf1

        Unintuitive as it may seem, Be6!! is the best move. The idea is to offer
        the queen in exchange for a fierce attack with minor pieces. Declining this
        offer is not: 18. Bxe6 leads to a 'Philidor Mate' (smothered mate) with ...Qb5+ 19. Kg1 Ne2+ 20. Kf1 Ng3+ 21. Kg1 Qf1+ 22. Rxf1 Ne2#. Other ways to decline the queen also run into trouble: e.g., 18. Qxc3 Qxc5

    Answer:

        g4e6


Example 2 (Bad):

    Explanation:

        In the given position, it's Black's turn to move, and the board looks like this:
        
        ```
          a b c d e f g h
        8 r n b q k b . r
        7 p p p p . p p p
        6 . . . . . n . .
        5 . . . . p . . .
        4 . . P P . . . .
        3 . . . . P . . .
        2 P P . . . P P P
        1 R N B Q K B N R
        ```
        
        As Black, a strong move here is **...dxc4**. This move captures the pawn on c4, gaining a material advantage and undermining White's pawn structure in the center.

    Answer:

        dxc4

    Why is this answer wrong?

        The answer should be in UCI notation. 'd7c4' is the correct answer.


Example 3 (Good):

    Explanation:

        Opening with 1. e4 is one of the most common and traditional choices for White. It sets up for open games, including the Spanish game (Ruy Lopez), Italian game, King's Gambit, etc., depending on Black's responses.
        
        1... c5 (Sicilian Defense)
        
           1.2. Nf3 and d4 to take control of the center. But the Sicilian Defense is known for creating an imbalanced game that gives both players chances for a win.
        
        1... e5 (Open Game)
        
          1.2. Nf3 aiming to attack the pawn at e5. If Black tries to protect the pawn, several promising lines such as Ruy Lopez and the Italian Game can occur.
        1... e6 (French Defense)
        
          1.2. d4 to dominate the center. This can lead to complex battles, some lines include the Advance, Tarrasch, and Winawer Variations.
        
        1... c6 (Caro-Kann Defense)
        
          1.2. d4 to hold the center, followed by 1. Nc3 or Nf3, depending on the black response. Both response leads to dynamic and strategic plans for both sides.
        
        1... d6 (Pirc Defense)
        
          2. d4 pushing the dominance in the center. 2. Nc3, Be3, or Nf3 can follow.
        
    Answer:

        e4


Example 4 (Bad):

    Explanation:

        Let’s analyze the current position carefully. The board is set up as follows:
        
        ```
        8 r n b . . . . r
        7 p p p k . p p .
        6 . . . . . . . .
        5 . . . Q . . . p
        4 P . . P . . . .
        3 . . P . P N . .
        2 . . . . B . P P
        1 R N . . K . . R
        ```
        
        **Best Move:**
        **Qe2 - Moving Queen back to e2 (defensive move)**
        
        **Explanation of Best Move:**
        - **Defensive Support:** This reinforces the defense against threats to the black king while helping shift the dynamic. The queen stays connected to the center and controls c4.
        - Any push you'd consider missing this opportunity leaves the king open to checks.
        
        While conceding material, it balances the board's activities and offers tactical chances in the next few moves to work towards safety. Going forward after this, options must be limited to strategic control over the center, developing pieces, and maybe commencing a pawn storm.

    Answer:

        d7e8

    Why is this answer wrong?

        d7e8 is not the suggested move. The suggested is Qe2, which is
        <> in UCI notation.

Example 5 (Good):

    Explanation:

        Thus far the game has progressed as follows:
        
        1. e4 e5 2. Nf3 d6 3. d4 Bg4?! 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6? 7. Qb3 
        
        Qe7 is the only good move. White is threatening mate in two moves,
        for example 7...Nc6 8.Bxf7+ Ke7 (or Kd7) 9.Qe6#. 7...Qd7 loses the
        rook to 8.Qxb7 followed by 9.Qxa8 (since 8...Qc6? would lose
        the queen to 9.Bb5). Notice that 7...Qe7 saves the rook with
        this combination: 8.Qxb7 Qb4+ forcing a queen exchange.
        
        Although this move prevents immediate disaster, I will be forced to block
        the f8-bishop, impeding development and kingside castling.

    Answer:

        d8e7


Your task is below.

Explanation:

{next_move_explanation}

Answer:
"""
    valid_moves = get_possible_moves(board)
    generator = outlines.generate.choice(model, valid_moves)
    move = generator(choice_prompt)

    print("*"*25)
    print(get_move_history(board))
    print(next_move_explanation)
    print(move)
    print("*"*25)
    return move

def get_white_move(board: chess.Board) -> str:
    #print("White: stockfish @ 1390")
    return stockfish_move(board, elo=1390)

def get_black_move(board: chess.Board) -> str:
    #print(f"Black: {model}")
    return ai_move(board, "gpt-4o-mini")
    #return stockfish_move(board, elo=1750)

def prettify_board(board: chess.Board) -> str:

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
    board_rows.append("  a b c d e f g h")
    for i, row in enumerate(str(board).splitlines()):
        for piece_name, piece_unicode in pieces.items():
            row = row.replace(piece_name, piece_unicode)

        board_rows.append(f"{8-i} {row}")

    return "\n".join(board_rows)

def draw_board(board):
    print(prettify_board(board))

def get_possible_moves(board: chess.Board) -> List[str]:
    moves = list(board.generate_legal_moves())
    moves = [str(move) for move in moves]
    return moves

board = ChessBoard()
draw_board(board)

#print("White: stockfish @ 1390")
#print("Black: gpt-4o-mini")

white = Stockfish(1320)
black = OpenAI()
#black = Random()
while not board.is_game_over():
    turn = board.waiting_on()
    move = white.get_move(board) if turn == "white" else black.get_move(board)
    board.submit_move(move)

    print()
    draw_board(board)
    print()

assert board.is_game_over()
draw_board(board)

# TODO: convert moves from UCI format to algebraic format
# Should probably subclass chess.Board to do this


results = {
    "1/2-1/2": "tie",
    "1-0": "white_win",
    "0-1": "black_win"
}
print(board.algebraic_history)
print(board.outcome())
print(board.get_move_history())

result = board.result()
print(results[result])

Stockfish.engine.close()
