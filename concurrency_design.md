
Brianna Miller<br>
CS457: Computer Networks and the Internet<br>
Sprint 2: Game Behavior & Server Concurrency Architecture Design<br>


### Detailed Architecture Specifications
#### Server Concurrency Model Selection
This trivia game will use multi-threading with a main thread for the server and two worker threads, one for each client socket. 
Having separate threads for each client will allow them to communicate with the server at the same time. The server will then be able to queue their requests before processing them in the game. Since the server is responsible for managing the shared resources in memory and preventing race conditions it can use a threading.Lock to coordinate access to resources that the threads could access at the same time.<br> 
The server will initialize the game state then listen for incoming connections. When a client connects to the server, the server will accept the connection and create a worker thread associated with that client. Then the server will register that client by adding their information to the game setup and creating a player name (e.g, player1 and player2). Once both clients are registered the game can begin. 
The active game loop will be controlled by the server and players will take turns throughout the game answering questions. The server will assign the active player a multiple choice question. Afterwards, the player can respond with an answer. Once the server receives the player's response, it will validate the answer by checking the turn order and processing the response.Then the server will process the response to determine if the and broadcast the score and turn updates using a STATE_UPDATE message. Broadcasting the updates will reflect changes in the game state for both players at the same time.<br>
Error and timeout handling:<br>
If a player attempts to answer out of turn or submits an invalid answer the server will send and ERROR message informing the client and ignore the request. 
If a player fails to answer a question within the round's time limit then a TIMEOUT message will be sent and the scores and turn order will be updated.<br> 
Once the game is complete and winner is determined, the server will broadcast the final scores by sending a GAME_OVER message. If a client indicates they want to quit by sending a QUIT message, then the server can begin handling the worker thread tear downs, closing the client connections and releasing the game's shared resources to end the game safely. Otherwise, the server will reset the game state and for the next game.


#### Mermaid Sequence Diagram
```mermaid
sequenceDiagram
    participant Client1
    participant Server
    participant Client2
    Client1->>Server: JOIN
    Server-->>Client1: LOBBY_WAIT
    Client2->>Server: JOIN

    Server-->>Client1: GAME_START
    Server-->>Client2: GAME_START

    loop each question/ turn(30 second time limit)
        Server-->>Client1: QUESTION
        Client1-->>Server: ANSWER
        Note over Server: Server validates: is it Client1's turn?

        alt Valid Answer within time limit
            Note over Server: Update Score Board<br>Switch Active Turn to Client2
            Server-->>Client1: STATE_UPDATE (Score, Turn: Client2)
            Server-->>Client2: STATE_UPDATE (Score, Turn: Client2)
        else Invalid / Out of Turn Move
            Server-->>Client1: ERROR ("Invalid Answer"/"Not Your Turn")
        else Timeout
            Server-->Client1: TIMEOUT ("Time Is Up")
            Note over Server: Update Score Board<br>Switch Active Turn to Client2
            Server-->>Client1: STATE_UPDATE (Score, Turn: Client2)
            Server-->>Client2: STATE_UPDATE (Score, Turn: Client2)
        else Player quits during game
            Client1->>Server: QUIT
            Note over Server: Player Left Game
            Server-->Client2:GAME_OVER(Winner, Message)
            Note over Server: Clean Up Game    
        end  

    end

    Server-->Client1:GAME_OVER
    Server-->Client2:GAME_OVER

    alt Players want to play again
        Note over Server: Reset Game
    else Client(s) wants to leave
        Client1->>Server: QUIT
        Note over Server: Clean Up Game
    end
```



