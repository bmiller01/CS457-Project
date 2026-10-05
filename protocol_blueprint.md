# CS 457 Sprint 1 Application Protocol & Game State Machine (FSM) Design

**Student Name:** Brianna Miller  
**Date:** 2026-10-04  
**Course:** CS 457 - Computer Networks  


### Application Protocol Blueprint
- **Transport Protocol:** TCP
- **Serialization Format:** Text Delimited Protocol
- **Message Types & Structured Schema Definitions:**  
    `JOIN` (Client -> Server): Client requests to join the game
       Format: MSG_TYPE|<PLAYER_ID>|<TIMESTAMP>\n
       Example: JOIN|Alice|1727000000\n
       Fields:
            - MSG_TYPE  (string): "JOIN"
            - PLAYER_ID (string): alphanumeric value to identify player that wants to join
            - TIMESTAMP (integer): Unix epoch timestamp seconds


    `LOBBY_WAIT` (Server -> Client): Server notifies exisiting client that it's waiting for another client to connect
       Format: MSG_TYPE|<PLAYER_ID>|<TIMESTAMP>\n
       Example: LOBBY_WAIT|Alice|1727000000\n
       Fields:
            - MSG_TYPE (string): "LOBBY_WAIT"
            - PLAYER_ID (string): alphanumeric value to identify player that is waiting
            - TIMESTAMP (integer): Unix epoch timestamp seconds


    `GAME_START` (Server -> Clients): Server notifies both clients that the game is starting
        Format: MSG_TYPE|<PLAYER1_ID>|<PLAYER2_ID>|<TIMESTAMP>\n
        Example: GAME_START|Alice|Bob|1727000000\n
        Fields:
            - MSG_TYPE      (string): "GAME_START"
            - PLAYER1_ID    (string): alphanumeric value to identify player1
            - PLAYER2_ID    (string): alphanumeric value to identify player2
            - TIMESTAMP     (integer): Unix epoch timestamp seconds


    `QUESTION` (Server -> Client): Server sends a trivia question and answer options to active client
        Format: MSG_TYPE|<QUESTION>|<OPTION_A>|<OPTION_B>|<OPTION_C>|<OPTION_D>\n
        Example: QUESTION|Which protocol is responsible for reliably delivering data between applications over a network?|IP|UDP|TCP|ARP|\n
        Fields:
            - MSG_TYPE (string): "QUESTION"
            - QUESTION (string): networking related trivia question
            - OPTION_A (string): Answer choice A
            - OPTION_B (string): Answer choice B
            - OPTION_C (string): Answer choice C
            - OPTION_D (string): Answer choice D
           - TIMESTAMP (integer): Unix epoch timestamp seconds


    `ANSWER` (Client -> Server): Active client submits the letter corresponding to their answer
        Format: MSG_TYPE|<OPTION>|<TIMESTAMP>\n
        Example: ANSWER|A|1727000000\n
        Fields:
            - MSG_TYPE  (string): "ANSWER"
            - OPTION    (char): letter corresponding to player's answer choice, options are A, B, C, or D (not case sensitive)
            - TIMESTAMP (integer): Unix epoch timestamp seconds


    `STATE_UPDATE` (Server -> Clients): Server broadcasts updated scoreboard active player's turn and timestamp
        Format: MSG_TYPE|<PLAYER1_ID>|<PLAYER1_SCORE>|<PLAYER2_ID>|<PLAYER2_SCORE>|<ACTIVE_PLAYER>|<TIMESTAMP>\n
        Example: STATE_UPDATE|Alice|5|Bob|3|Alice|1727000000\n
        Fields:
            - MSG_TYPE      (string): "STATE_UPDATE"
            - PLAYER1_ID    (string): alphanumeric value to identify player1
            - PLAYER1_SCORE (integer): current score for player1
            - PLAYER2_ID    (string): alphanumeric value to identify player2
            - PLAYER2_SCORE (integer): current score for player2
            - ACTIVE_PLAYER (string): Player ID of the player whose turn is active
            - TIMESTAMP     (integer): Unix epoch timestamp seconds


    `QUIT` (Client -> Server): Client notifies server they want to quit
        Format: MSG_TYPE|<PLAYER_ID>|<TIMESTAMP>\n
        Example: QUIT|Alice|1727000000\n
        Fields:
            - MSG_TYPE  (string): "QUIT"
            - PLAYER_ID (string): alphanumeric value to identify player that wants to quit
            - TIMESTAMP (integer): Unix epoch timestamp seconds


    `ERROR` (Server -> Client): Server notifies client that their answer was invalid or out of turn
        Format: MSG_TYPE|<PLAYER_ID>|<TIMESTAMP>\n
        Example: ERROR|Alice|1727000000\n
        Fields:
            - MSG_TYPE  (string): "ERROR"
            - PLAYER_ID (string): alphanumeric value to identify player that made an invalid choice or action
            - TIMESTAMP (integer): Unix epoch timestamp seconds


    `TIMEOUT` (Server -> Clients): Server notifies clients that the active player did not answer within the time limit
        Format: MSG_TYPE|<PLAYER_ID>|<TIMESTAMP>\n
        Example: TIMEOUT|Alice|1727000000\n
        Fields:
            - MSG_TYPE  (string): "TIMEOUT"
            - PLAYER_ID (string): alphanumeric value to identify player that did not answer within the allotted time
            - TIMESTAMP (integer): Unix epoch timestamp seconds
       

    `GAME_OVER` (Server -> Clients): Server notifies clients that the game has ended and shows the final scores
        Format: MSG_TYPE|<PLAYER1_ID>|<PLAYER1_SCORE>|<PLAYER2_ID>|<PLAYER2_SCORE>|<WINNER>|<TIMESTAMP>\n
        Example: GAME_OVER|Alice|8|Bob|7|Alice|1727000000\n
        Fields:
            - MSG_TYPE      (string): "GAME_OVER"
            - PLAYER1_ID    (string): alphanumeric value to identify player1
            - PLAYER1_SCORE (integer): current score for player1
            - PLAYER2_ID    (string): alphanumeric value to identify player2
            - PLAYER2_SCORE (integer): current score for player2
            - WINNER        (string): Player ID of the player who won
            - TIMESTAMP     (integer): Unix epoch timestamp seconds


- **TCP Stream Packet Framing & Boundary Handling:**
    Each message field is seperated by a '|' delimiter and each completed message is terminated with a newline '\n' delimiter. Since a single message might be split across multiple recv() calls, it would be helpful to have a buffer to store the incoming data. When a '\n' character is encountered, that indicates that a full message was received and everything before the '\n' can be processed as one complete message.
    For example a buffer could store: 
    `GAME_START|Alice|Bob|1727000000\nSTATE_UPDATE|Alice|0|Bob|0|`
    The receiver could process the data in the buffer by searching for the newline character and group everything before it as one complete message. The remaining data in the buffer `STATE_UPDATE|Alice|0|Bob|0|` doesn't have a '\n' delimiter at the end so the receiver would wait for more data before processing that message.

- **Connection Termination & Socket Lifecycle Management:**
    When the client sends a QUIT message, the server can gracefully disconnect with a normal TCP FIN teardown and clean up the connection. If there is an abrupt termination, like a network drop, then the server could receive a TCP RST packet and encounter a ConnectionResetError exception that it has to handle before cleaning up the connection. A TCP 0-byte EOF occurs when a client closes its socket and can no longer receive data. If the server ignores the EOF and tries sending more data it could encounter a BrokenPipeError exception that needs to be handled before cleaning up the connection.
     

