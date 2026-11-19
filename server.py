#!/usr/bin/env python3
"""Two-player Terminal Trivia TCP server for CS457."""

import argparse
import queue
import random
import socket
import threading
import time

HOST = "0.0.0.0"
TURN_SECONDS = 30

# Each question is (prompt, four options, correct option, explanation).
QUESTIONS = [
    ("Which transport protocol provides reliable, ordered delivery?",
     ["UDP", "TCP", "IP", "ARP"], "B",
     "TCP provides reliable, ordered byte-stream delivery."),
    ("Which OSI layer is responsible for logical addressing and routing?",
     ["Data Link", "Transport", "Network", "Application"], "C",
     "The Network layer handles logical addressing and routing."),
    ("What is the default port for DNS?",
     ["22", "53", "80", "443"], "B", "DNS conventionally uses port 53."),
    ("Which protocol dynamically assigns IP configuration to clients?",
     ["DHCP", "FTP", "SMTP", "SNMP"], "A",
     "DHCP assigns IP addresses and other network configuration."),
    ("Which TCP flag begins a typical connection handshake?",
     ["FIN", "RST", "ACK", "SYN"], "D",
     "A TCP connection normally begins with a SYN packet."),
    ("What does CIDR /24 represent in an IPv4 network?",
     ["24 host bits", "24 network bits", "24 subnets", "24 routers"], "B",
     "A /24 prefix contains 24 network bits."),
    ("Which device forwards frames using MAC address tables?",
     ["Router", "Switch", "Hub", "Repeater"], "B",
     "A Layer 2 switch forwards frames using MAC addresses."),
    ("What does ARP resolve on a local IPv4 network?",
     ["Name to IP", "IP to MAC", "Port to process", "MAC to DNS name"], "B",
     "ARP maps an IPv4 address to a MAC address."),
    ("Which DNS record maps a hostname to an IPv4 address?",
     ["AAAA", "MX", "A", "PTR"], "C",
     "An A record maps a hostname to an IPv4 address."),
    ("Which TCP value advertises the receiver's available buffer capacity?",
     ["Congestion window", "Receive window", "Routing metric", "TTL"], "B",
     "The advertised receive window supports TCP flow control."),
]

TIEBREAKERS = [
    ("Which IPv4 header field prevents packets circulating indefinitely?",
     ["Checksum", "TTL", "IHL", "DSCP"], "B",
     "Routers decrement TTL at each hop."),
    ("Which protocol secures web traffic using TLS?",
     ["HTTP", "HTTPS", "TFTP", "Telnet"], "B",
     "HTTPS is HTTP protected by TLS."),
]


class Player:
    """Connected player and the lock protecting writes to the socket."""

    def __init__(self, sock, address, name):
        self.sock = sock
        self.address = address
        self.name = name
        self.score = 0
        self.connected = True
        self.send_lock = threading.Lock()


def send_message(player, *fields):
    """Send one pipe-delimited, newline-terminated protocol message."""
    message = "|".join(str(value).replace("|", "/").replace("\n", " ")
                      for value in fields) + "\n"
    try:
        with player.send_lock:
            player.sock.sendall(message.encode("utf-8"))
    except OSError:
        player.connected = False


def broadcast(players, *fields):
    for player in players:
        if player.connected:
            send_message(player, *fields)


def read_join(conn):
    """Read the first complete line and validate its JOIN message."""
    conn.settimeout(30)
    buffer = b""
    while b"\n" not in buffer:
        chunk = conn.recv(4096)
        if not chunk:
            raise ConnectionError("Client disconnected before joining.")
        buffer += chunk
        if len(buffer) > 8192:
            raise ValueError("JOIN message is too large.")
    line = buffer.split(b"\n", 1)[0].decode("utf-8", errors="replace")
    fields = line.strip().split("|")
    if len(fields) < 2 or fields[0] != "JOIN":
        raise ValueError("Expected JOIN|player_name|timestamp.")
    return fields[1][:20] or "Player"


def client_reader(player, incoming):
    """Worker thread: receive complete messages and queue them for the game."""
    buffer = b""
    try:
        player.sock.settimeout(None)
        while player.connected:
            chunk = player.sock.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line:
                    fields = line.decode("utf-8", errors="replace").split("|")
                    incoming.put((player, fields))
    except OSError:
        pass
    finally:
        player.connected = False
        incoming.put((player, ["DISCONNECT"]))


def send_question(player, question, number, total, deadline):
    prompt, options, _, _ = question
    send_message(player, "QUESTION", number, total, prompt, *options,
                 int(deadline))


def send_scores(players, active):
    first, second = players
    broadcast(players, "STATE_UPDATE", first.name, first.score,
              second.name, second.score, active.name, int(time.time()))


def main():
    parser = argparse.ArgumentParser(description="Two-player Terminal Trivia server")
    parser.add_argument("-p", "--port", type=int, required=True,
                        help="TCP port on which the server listens")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, args.port))
    server_socket.listen(2)
    print(f"[SERVER] Listening on {HOST}:{args.port}")

    players = []
    try:
        while len(players) < 2:
            connection, address = server_socket.accept()
            try:
                name = read_join(connection)
                player = Player(connection, address, name)
                players.append(player)
                send_message(player, "LOBBY_WAIT", name, int(time.time()))
                print(f"[SERVER] {name} connected from {address}")
                if len(players) == 1:
                    print("[SERVER] Waiting for Player 2...")
            except (OSError, ValueError, ConnectionError) as error:
                print(f"[SERVER] Rejected connection: {error}")
                connection.close()

        server_socket.close()
        broadcast(players, "GAME_START", players[0].name,
                  players[1].name, int(time.time()))
        incoming = queue.Queue()
        for player in players:
            threading.Thread(target=client_reader,
                             args=(player, incoming), daemon=True).start()

        print("[SERVER] Both players connected. Game started.")
        active_index = 0
        game_over = False

        def play_turn(question, number, total):
            """Run one 30-second turn; return True only for a correct answer."""
            nonlocal active_index, game_over
            active = players[active_index]
            waiting = players[1 - active_index]
            deadline = time.monotonic() + TURN_SECONDS
            send_question(active, question, number, total, deadline)
            send_message(waiting, "WAIT_TURN", active.name, int(time.time()))

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    send_message(active, "TIMEOUT", active.name, int(time.time()))
                    broadcast(players, "FEEDBACK",
                              f"{active.name} ran out of time. No point awarded.")
                    active_index = 1 - active_index
                    send_scores(players, players[active_index])
                    return False
                try:
                    sender, fields = incoming.get(timeout=remaining)
                except queue.Empty:
                    continue

                if fields[0] in ("DISCONNECT", "QUIT"):
                    sender.connected = False
                    winner = waiting if sender is active else active
                    broadcast(players, "GAME_OVER", players[0].name,
                              players[0].score, players[1].name,
                              players[1].score,
                              winner.name if winner.connected else "NONE",
                              int(time.time()))
                    game_over = True
                    return False

                if sender is not active:
                    send_message(sender, "ERROR", sender.name,
                                 "It is not your turn", int(time.time()))
                    continue
                if fields[0] != "ANSWER" or len(fields) < 2:
                    send_message(sender, "ERROR", sender.name,
                                 "Expected ANSWER|A/B/C/D|timestamp",
                                 int(time.time()))
                    continue

                answer = fields[1].strip().upper()
                if answer not in ("A", "B", "C", "D"):
                    send_message(sender, "ERROR", sender.name,
                                 "Answer must be A, B, C, or D", int(time.time()))
                    continue

                correct = answer == question[2]
                if correct:
                    active.score += 1
                    broadcast(players, "FEEDBACK",
                              f"{active.name} answered correctly! +1 point.")
                else:
                    broadcast(players, "FEEDBACK",
                              f"{active.name} answered incorrectly. "
                              f"Correct answer: {question[2]}. {question[3]}")
                active_index = 1 - active_index
                send_scores(players, players[active_index])
                return correct

        for number, question in enumerate(QUESTIONS, start=1):
            if not all(player.connected for player in players):
                game_over = True
                break
            play_turn(question, number, len(QUESTIONS))
            if game_over:
                break

        if not game_over and all(player.connected for player in players):
            if players[0].score == players[1].score:
                broadcast(players, "FEEDBACK",
                          "The score is tied! Starting sudden-death tiebreaker.")
                while not game_over:
                    question = random.choice(TIEBREAKERS)
                    correct = play_turn(question, "TB", "TB")
                    if game_over:
                        break
                    if correct:
                        winner = players[1 - active_index]
                        broadcast(players, "GAME_OVER", players[0].name,
                                  players[0].score, players[1].name,
                                  players[1].score, winner.name, int(time.time()))
                        game_over = True
            else:
                winner = max(players, key=lambda item: item.score)
                broadcast(players, "GAME_OVER", players[0].name,
                          players[0].score, players[1].name,
                          players[1].score, winner.name, int(time.time()))
        print("[SERVER] Game finished.")
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down.")
    finally:
        server_socket.close()
        for player in players:
            try:
                player.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            player.sock.close()


if __name__ == "__main__":
    main()
