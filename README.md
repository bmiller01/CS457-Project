# CS457 Terminal Trivia

A two-player console trivia game using TCP sockets, newline-delimited,
pipe-separated messages, a threaded server, and a server-controlled game loop.

## Run

On the server node:

```bash
python3 server.py -p 8080
```

On each of the two client nodes:

```bash
python3 client.py -i server.smith.edu -p 8080
```

Replace `server.smith.edu` with the DNS hostname configured for your CML project.
For local testing on one computer, run the server and two clients in separate
terminals and use `127.0.0.1` as the hostname.

## Rules

- Exactly two players.
- Ten networking questions, with alternating turns.
- Each turn has a 30-second time limit.
- Correct answers earn one point; incorrect answers and timeouts earn zero.
- A tie after the ten questions starts a sudden-death tiebreaker.
- No hints, question swaps, or streak bonuses.

## Implementation

The server binds to `0.0.0.0`. Its main thread controls game-state transitions.
One reader thread per client receives messages and places them on a thread-safe
queue. A per-client lock protects socket writes. TCP messages are UTF-8,
pipe-delimited, and terminated by a newline.

The client resolves the hostname with `socket.gethostbyname()`. A DNS
`socket.gaierror` is caught and reported with a user-friendly message; the client
exits with status code 1.

## CML deployment

The original SOW describes two client nodes on separate client subnets and one
server node on the server subnet, connected through the routers. Configure DNS
so the server hostname resolves to the server node's IP address before testing
the hostname-based client command.

Capture a terminal screenshot or log showing both clients connected and at
least three completed turns for the gameplay deliverable.
