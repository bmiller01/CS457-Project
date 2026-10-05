    [*] --> INIT
    INIT --> WAITING_FOR_PLAYERS : Server started and listening for connections
    WAITING_FOR_PLAYERS --> START_GAME : 2 clients connected to server
    WAITING_FOR_PLAYERS --> CLEAN_UP : Client disconnects before game starts
    START_GAME --> PLAYER_TURN : Scoreboard initialized & turn order assigned

    PLAYER_TURN --> EVALUATE_RESPONSE : Current client sends response
    PLAYER_TURN --> PLAYER_TURN : Out-of-turn response / send ERROR message
    PLAYER_TURN --> GAME_OVER : Client disconnects abruptly / remaining client declared winner
    PLAYER_TURN --> PLAYER_TURN : Response timeout/ switch turn

    EVALUATE_RESPONSE --> PLAYER_TURN : Valid response /Update scoreboard & switch turn
    EVALUATE_RESPONSE --> PLAYER_TURN : Invalid response (send ERROR message to client)
    EVALUATE_RESPONSE --> SCORE_CHECK : Final question answered

    SCORE_CHECK --> GAME_OVER : Scores are different
    SCORE_CHECK --> TIEBREAKER : Scores are tied

    TIEBREAKER --> TIEBREAKER : Out-of-turn response / send ERROR message
    TIEBREAKER --> TIEBREAKER : Response timeout / switch turn
    TIEBREAKER --> GAME_OVER : Client disconnects abruptly / remaining client declared winner
    TIEBREAKER --> EVALUATE_TIEBREAKER_RESPONSE : Current client sends response
    EVALUATE_TIEBREAKER_RESPONSE --> TIEBREAKER : Incorrect response/ switch turn
    EVALUATE_TIEBREAKER_RESPONSE --> TIEBREAKER : Invalid response (send ERROR message to client)
    EVALUATE_TIEBREAKER_RESPONSE --> GAME_OVER : Correct response / winner determined

    GAME_OVER --> CLEAN_UP : Broadcast final scores and message
    CLEAN_UP --> WAITING_FOR_PLAYERS : Reset for next game
    CLEAN_UP --> [*] : Disconnect
