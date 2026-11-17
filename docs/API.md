# Shared State-Wordle API

## Endpoints

### GET /games/\<game_id\>

Returns the current state of a game. It is only available to players who have participated the game.

| STATUS | BODY          | WHEN |
| ------ | ------------- | ---- |
| 200    | **SEE BELOW** | On success |


Upon success you can expect the following output. Please note that order of the keys might not be exactly as described below (with the exception of "players", and "guesses"). *However*, there are a few fields which you can expect to differ regularly.

- `"ended_at"` will be null if the game was not finished.
- `"current_turn"` on exists once two players are in a game
- `"answer"` only appears when `"status" = "finsihed"`

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