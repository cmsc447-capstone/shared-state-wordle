# Shared State-Wordle API

## Game State

### GET /games/\<game_id\>

**Retrieve game state**. The game state can be retrieved at any point only by the games participants. The answer is only returned when the game is finished. `ended_at`, `players`, `guesses`, and `current_turn` changes through game progression. 


```json
{
    "game_id": "<uuid>",
    "status": "started",
    "created_at": "<timestamp>",
    "ended_at" : "<timestamp>",
    "language": "<language>",
    "players": [
        {"player_id": "uuid",
         "username": "<name>",
         "turn_order": 1,
         "result": null
        },
        {"player_id": "uuid",
         "username": "<name>",
         "turn_order": 2,
         "result": null
        }
    ],
    "guesses": [
        {"attempt_num": 1,
         "player_id": "<uuid>",
         "word": "<guess>",
         "feedback": "",            // Please check with feedback team
         "made_at": "<timestamp>"
        }
    ],
    "current_turn": "<uuid>",
    "answer": "<answer>"
}
```

#### **Errors**
| CODE | JSON          | MEANING |
| ---- | ------------- | ---- |
| 200  | **SEE BELOW** | On success |
| 403  | `{"error": "You did not play in this game"}` | If an unauthorized user is attempting to get the game state.
| 404 | `{"error": "No game found with that game_id"}` | If the game_id is not listed in the database.

---
---

## Matchmaking

### POST /games/match

**Join matchmaking.** A player is only allowed to join matchmaking if they are not already in an active game. If the route is called twice, a 202 is returned and the player *will* keep their place in line. 


Status code 201. Player was match immediately.
```json
{
    "queued": False,
    "game_id": <game_id>
}
```
---

Status code 202. Enqueued, no match was available.
```json
{
    "queued": True,
    "game_id": None
}
```

#### **Errors**
| CODE | JSON  | MEANING |
| ---- | ----- | ------- |
| 409  | `{"error": "You are already in a game"}` | Player tried to queue while in an active game

---

### DELETE /games/match

**Exit matchmaking**. A player leaves matchmaking and is dequeued. A player is automatically removed from matchmaking if, they are matched with another player in the matchmaking pool and create or accept a game invite.

Status code is *always* 204. This makes it safe to call when when not in matchmaking.

---
---

## Invites

### POST /games

**Create invite**. A player is allowed to create a game invite only if they are not already in an active game. 

Status code 201. Game was created.

```json
{
    "game_id": <game_id>,
    "game_status": "waiting",
    "language": <language>
}
```

#### **Errors**
| CODE | JSON  | MEANING |
| ---- | ----- | ------- |
| 409  | `{"error": "You are already in a game"}` | Player tried to create invite while in an active game.

---

### DELETE /games/\<uuid:game_id\>

**Cancel invite**. Only the host is allowed to cancel an invite. An invite can only be cancelled if the game is not active. Outgoing invites are automatically cancelled when a player joins matchmaking or attempts to accept a _**different**_ invite.

Successful status code is 204.

#### **Error Codes**
| CODE | JSON  | MEANING |
| ---- | ----- | ------- |
| 403  | `{"error": "Only the host can canel this game"}` | Player attempted to cancel a game they were not the host for.
| 404  | `{"error": "No game found with that game_id}` | Player attempted to cancel a game that did not exist.
| 409  | `{"error": "you cannot cancel this game"}` | Player attempted to cancel a game that was in progress.
| 409  | `{"error": "game already in progress"}` | Player attempted to cancel a game but the guest joined during the transaction.

---

### POST /games/\<uuid:game_id\>/join

An invite can only be accepted if the recipient is not currently in an active game. A player is only allowed to accept an invite that they did not create.  

Status code 201. Game was created.

```json
{
    "game_id": <game_id>,
    "game_status": "started",
    "turn_order": 2
}
```

#### **Error Codes**
| CODE | JSON  | MEANING |
| ---- | ----- | ------- |
| 404  | `{"error": "No game found with that game_id"}` | Player attempted to join a game that does not exist.
| 409  | `{"error": "This game is already in progress"}` | Player attempted to join an active game.
| 409  | `{"error": "You are already in this game"}` | Player attempted to join their own game.
| 409  | `{"error": "This game is full"}` | Player attempted to join accept the invite but another player joined before their transaction was complete. 
| 409  | `{"error": "You are already in a game"}` | Player attempted to join while in an active game.

---
---

## User login

### POST /users/login

**Logs in an *existing* user**. If the credentials are valid, the server returns the user's information and Supabase authentication tokens.

The `access_token` is used to authenticate subsequent API requests through the `Authorization: Bearer <access_token>` header. The `refresh_token` is used to obtain a new access token when the current one expires. `expires_at` indicates when the access token expires. The `user_id` identifies the authenticated user. The `username` identifies the user within the application.


Status code 201. Successful login


```json
{
    "user_id": "<user_id>",
    "username": "<username>",
    "access_token": "<access_token>",
    "refresh_token": "<refresh_token>",
    "expires_at": "<expiration_timestamp>"
}
```

#### **Error Codes**
| CODE | JSON  | MEANING |
| ---- | ----- | ------- |
| 401 | `{"error": "Invalid email or password"}` | If the email or password is incorrect |

---
---