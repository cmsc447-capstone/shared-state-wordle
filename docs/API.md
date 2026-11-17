# Shared State-Wordle API

## Endpoints

### GET /games/\<game_id\>

Returns the current state of a game. It is **only** available to players who have participated the game.

| STATUS | BODY          | WHEN |
| ------ | ------------- | ---- |
| 200    | **SEE BELOW** | On success |
| 403    | `{"error": "You did not play in this game"}` | If an unauthorized user is attempting to get the game state.
| 404    | `{"error": "No game found with that game_id"}` | If the game_id is not listed in the database.

The following output is what you can expect to recieve on successful calls. Please note that the order of the keys might not match exactly as described/

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