#!/usr/bin/env python3
"""Command-line client for the CS457 Terminal Trivia game."""

import argparse
import select
import socket
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(
        description="Connect to a two-player Terminal Trivia server")
    parser.add_argument(
        "-i", "--hostname", required=True,
        help="Server DNS hostname, for example server.smith.edu")
    parser.add_argument("-p", "--port", type=int, required=True,
                        help="Server TCP port")
    return parser.parse_args()


def send_message(sock, *fields):
    """Send one pipe-delimited, newline-terminated protocol message."""
    message = "|".join(str(value).replace("|", "/").replace("\n", " ")
                       for value in fields) + "\n"
    sock.sendall(message.encode("utf-8"))


def main():
    args = parse_args()
    if not 1 <= args.port <= 65535:
        print("[ERROR] Port must be between 1 and 65535.")
        return 1

    try:
        server_ip = socket.gethostbyname(args.hostname)
    except socket.gaierror:
        print(f"[ERROR] Unable to resolve DNS hostname '{args.hostname}'.")
        print("Please check your Cisco router DNS configuration "
              "('ip dns server' / 'ip host') or verify domain spelling.")
        return 1

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, args.port))
    except OSError as error:
        print(f"[ERROR] Could not connect to "
              f"{args.hostname}:{args.port}: {error}")
        client_socket.close()
        return 1

    player_name = input("Enter your player name: ").strip()[:20] or "Player"
    try:
        send_message(client_socket, "JOIN", player_name, int(time.time()))
        print(f"[CLIENT] Connected to {args.hostname} "
              f"({server_ip}:{args.port}).")
        print("[CLIENT] Waiting for another player...")

        buffer = ""
        your_turn = False
        answer_buffer = ""

        while True:
            # Windows select() supports sockets, not stdin. Monitor only the
            # socket here and read keyboard characters with msvcrt below.
            readable, _, _ = select.select([client_socket], [], [], 0.1)

            if client_socket in readable:
                data = client_socket.recv(4096)
                if not data:
                    print("[CLIENT] Server closed the connection.")
                    break
                buffer += data.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line:
                        continue
                    fields = line.split("|")
                    message_type = fields[0]

                    if message_type == "LOBBY_WAIT":
                        print("[CLIENT] Waiting for Player 2...")
                    elif message_type == "GAME_START":
                        print(f"\n[GAME START] {fields[1]} vs {fields[2]}")
                    elif message_type == "QUESTION":
                        number, total = fields[1], fields[2]
                        prompt = fields[3]
                        options = fields[4:8]
                        your_turn = True
                        answer_buffer = ""
                        print("\n" + "-" * 58)
                        print(f"QUESTION {number}/{total} — YOUR TURN")
                        print(prompt)
                        for letter, option in zip("ABCD", options):
                            print(f"{letter}) {option}")
                        print("You have 30 seconds. Enter A, B, C, or D.")
                        print("Answer: ", end="", flush=True)
                    elif message_type == "WAIT_TURN":
                        your_turn = False
                        answer_buffer = ""
                        print(f"\n[WAITING] It is {fields[1]}'s turn.")
                    elif message_type == "TIMEOUT":
                        your_turn = False
                        answer_buffer = ""
                        print("\n[TIMEOUT] Your 30 seconds expired.")
                    elif message_type == "STATE_UPDATE":
                        your_turn = False
                        answer_buffer = ""
                        print("\n[SCOREBOARD]")
                        print(f"  {fields[1]}: {fields[2]} points")
                        print(f"  {fields[3]}: {fields[4]} points")
                        print(f"  Next turn: {fields[5]}")
                    elif message_type == "FEEDBACK":
                        print(f"\n{fields[1]}")
                    elif message_type == "ERROR":
                        print(f"\n[ERROR] {' — '.join(fields[1:-1])}")
                    elif message_type == "GAME_OVER":
                        your_turn = False
                        print("\n" + "=" * 58)
                        print("[GAME OVER]")
                        print(f"{fields[1]}: {fields[2]} points")
                        print(f"{fields[3]}: {fields[4]} points")
                        print(f"Winner: {fields[5]}")
                        print("=" * 58)
                        return 0

            if your_turn:
                if sys.platform == "win32":
                    import msvcrt

                    while msvcrt.kbhit():
                        char = msvcrt.getwch()
                        if char in ("\x00", "\xe0"):
                            if msvcrt.kbhit():
                                msvcrt.getwch()
                        elif char in ("\r", "\n"):
                            answer = answer_buffer.strip().upper()
                            print()
                            if answer in ("A", "B", "C", "D"):
                                send_message(client_socket, "ANSWER", answer,
                                             int(time.time()))
                                your_turn = False
                                answer_buffer = ""
                            else:
                                print("Please enter A, B, C, or D.")
                                print("Answer: ", end="", flush=True)
                                answer_buffer = ""
                        elif char == "\b":
                            if answer_buffer:
                                answer_buffer = answer_buffer[:-1]
                                print("\b \b", end="", flush=True)
                        elif char.isprintable():
                            answer_buffer += char
                            print(char, end="", flush=True)
                else:
                    input_ready, _, _ = select.select([sys.stdin], [], [], 0)
                    if sys.stdin in input_ready:
                        answer = sys.stdin.readline().strip().upper()
                        if answer in ("A", "B", "C", "D"):
                            send_message(client_socket, "ANSWER", answer,
                                         int(time.time()))
                            your_turn = False
                        else:
                            print("Please enter A, B, C, or D.")
                            print("Answer: ", end="", flush=True)

    except (OSError, UnicodeError) as error:
        print(f"[ERROR] Network communication failed: {error}")
        return 1
    finally:
        client_socket.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
