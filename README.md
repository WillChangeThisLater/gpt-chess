## What is this?
This is largely a response to [this article](https://dynomight.net/chess/). The author got a bunch of OpenAI
models to play chess, and found that they pretty much universally sucked.
[He improves them a bit here](https://dynomight.net/more-chess/) but he wasn't able to get
them to play particularlly well in general.

I wanted to see if I could do better. From what I recall, the way the author prompted
the model is by providing a series of moves in algebraic notation

```moves
1. c3 e5
2. e4 d5
3. d4 dxe4
4. Qc2 Nf6
5. Ne2 Bf5
6. Ng3 Bc5
7. Nxf5 Nbd7
8. dxc5 Nxc5
9. Be3 Qd5
10. Bb5+ c6
11. Bxc5 Qxc5
12. Be2 O-O
13. O-O e3
14. Nxe3 e4
15. Na3 Qf5
16. h4 h5
17. Nxf5 Rfe8
18. Ne3
```

Plucking the next move from this is ok I guess? But I thought I could do better
by asking the model to think like a grandmaster and generate a next best move
with an explanation.

## How well does the AI play?
Pretty terribly. It consistently loses to the 1390 ELO stockfish model.
There are a bunch of different errors that might be coming into play here.
My bet it still that you can get the model to perform reasonable-ish with
enough prompt tuning but it's much harder than I initially thought.
