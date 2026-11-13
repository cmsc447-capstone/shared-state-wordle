# CMSC447 - Shared-State Wordle
# The following test cover all game managment routes
#   POST    /games
#   POST    /games/<game_id>/join
#   GET     /games/<game_id>

import uuid
from datetime import datetime, timezone

NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"

""" POST /games """

def test_create_game(client, sofia):
    r = client.post("/games", json={"language": "eng"}, headers=sofia["headers"])

    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "waiting"  # waiting for second player to join
    assert body["language"] == "eng"    # langauge matches perferred langauge
    uuid.UUID(body["game_id"])          # verifies a valid UUID
    assert "answer" not in body         # game not finished so no answer should be present

# create_game should automatically write into plays and asnwer table
def test_create_game_writes_plays_and_answer(client, sofia, db, db_rows):
    r = client.post("/games", json={"language": "eng"}, headers=sofia["headers"])
    game_id = r.get_json()["game_id"]

    plays = db_rows(db.table("plays")           # SELECT *
                    .select("*")                # FROM plays
                    .eq("game_id", game_id)     # WHERE game_id == game_id
                    .execute())
    assert len(plays) == 1                      # So far only sofia plays in this game
    assert plays[0]["player_id"] == sofia["id"] # sofia ID matches player id in plays as player 1
    assert plays[0]["turn_order"] == 1          # sofia has the first turn

    answer = db_rows(db.table("answer")         # SELECT *
                     .select("*")               # FROM answer 
                     .eq("game_id", game_id)    # WHERE game_id == game_id
                     .execute())
    assert len(answer) == 1                 # this game should only have one answer
    assert answer[0]["language"] == "eng"   # answer language should match player language
    assert len(answer[0]["word"]) == 5      # lenght of answer word should be 5 letters 

# the language of the answer word should match the player language
# player language is English by deafult
def test_create_game_player_language(client, sofia):
    r = client.post("/games", json={}, headers=sofia["headers"])

    assert r.status_code == 201
    assert r.get_json()["language"] == "eng"

def test_create_game_player_langauge_unknonwn(client, sofia, db , db_rows):
    r = client.post("/games", json={"language": "fra"}, headers=sofia["headers"])

    assert r.status_code == 400 # 400 is the error code for unknown language
    assert "error" in r.get_json()

    plays = db_rows(db.table("plays")               # SELECT game_id
                   .select("game_id")               # FROM plays 
                   .eq("player_id", sofia["id"])    # WHERE player_id == sofia.id
                   .execute()) 
    assert plays == [] # Failed games should be removed from that database

# When creating a game a valid token is required should you attempt
# to create a game with no token you should get a 401 error
def test_create_game_no_token(client):
    r = client.post("/games", json={"language": "eng"})
    assert r.status_code == 401

# When creating a game a valid token is required should you attempt
# to create a game with an invalid token you should get a 401 error
def test_create_game_bad_token(client):
    r = client.post("/games", json={"language": "eng"}, headers={"Authorization": "Bearer bad-token"})
    assert r.status_code == 401

""" POST /games/<game_id>/join """

def test_join_game(client, sofia, grace, create_game):
    game_id = create_game(sofia)

    r = client.post(f"/games/{game_id}/join", headers=grace["headers"])

    assert r.status_code == 200         # P2 (grace) was able to join the game
    body = r.get_json()
    assert body["status"] == "started"  # the game status was updated to "started" from "waiting"
    assert body["turn_order"] == 2      # P2 (grace) plays her turn after P1 (sofia)

def test_join_own_game(client, sofia, create_game):
    game_id = create_game(sofia)
    r = client.post(f"/games/{game_id}/join", headers=sofia["headers"])
    assert r.status_code == 409 # You cannot join your own game

def test_join_full_game(client, sofia, grace, julia, create_game):
    game_id = create_game(sofia)
    client.post(f"/games/{game_id}/join", headers=grace["headers"])      # grace joins the game as normal
    r = client.post(f"/games/{game_id}/join", headers=julia["headers"])  # julia tries to join the game
    assert r.status_code == 409 # julia cannot join because grace has already joined

def test_join_nonexistent_game(client, grace):
    r = client.post(f"game/{NONEXISTENT_ID}/join", headers=grace["headers"])
    assert r.status_code == 404 # You cannot join a game that does not exists (NO game_id)

def test_join_bad_game_id(client, grace):
    r = client.post(f"games/bad-id/join", headers=grace["headers"])
    assert r.status_code == 404 # You cannot join a game with an invalid game_id

def test_join_game_no_token(client, grace, create_game):
    game_id = create_game(grace)
    r = client.post(f"/games/{game_id}/join") # No headers means no token
    assert r.status_code == 401

def test_player_creates_two_games(client, sofia, create_game):
    create_game(sofia)
    r = client.post("/games", json={"language": "eng"}, headers=sofia["headers"])
    assert r.status_code == 409 # you can only create one game at a time

def test_create_after_joining(client, sofia, grace, create_game):
    game_id = create_game(sofia)
    client.post(f"/games/{game_id}/join", headers=grace["headers"])
    r = client.post("/games", json={"language": "eng"}, headers=grace["headers"])
    assert r.status_code == 409 # you can't create another game if you in an active one (player 2)

def test_create_after_joined(client, sofia, grace, create_game):
    game_id = create_game(sofia)
    client.post(f"/games/{game_id}/join", headers=grace["headers"])
    r = client.post("/games", json={"language": "eng"}, headers=sofia["headers"])
    assert r.status_code == 409 # you can't create another game if you in an active one (player 1)

""" GET /games/<game_id> """

def test_get_started_game(client, sofia, julia, create_game):
    game_id = create_game(sofia)
    client.post(f"/games/{game_id}/join", headers=julia["headers"])
    r = client.get(f"/games/{game_id}", headers=julia["headers"])

    assert r.status_code == 200         # game retrieved successfully
    state = r.get_json()
    assert state["game_id"] == game_id          # game_id matches requested
    assert state["status"]  == "started"        # game state is started
    assert state["language"] == "eng"           # game language matches sofia's perferred langauge
    assert state["guesses"] == []               # no guesses have been made
    assert state["current_turn"] == sofia["id"] # P1 (sofia) goes first
    assert "answer" not in state                # answer should only appear in finished games

    players = {p["turn_order"]: p for p in state["players"]}
    assert players[1]["player_id"]  == sofia["id"]
    assert players[1]["username"]   == sofia["username"]
    assert players[2]["player_id"]  == julia["id"]
    assert players[2]["username"]   == julia["username"]

def test_get_waiting_game(client, grace, create_game):
    game_id = create_game(grace)
    r = client.get(f"/games/{game_id}", headers=grace["headers"])

    assert r.status_code == 200         # game retrieved successfully
    state = r.get_json()
    assert state["status"] == "waiting"     # game state is "waiting" for P2
    assert state["current_turn"] is None    # no turns have been assigned yet
    assert len(state["players"]) == 1       # only host (grace) has joined

def test_get_finished_game(client, grace, julia, create_game, db):
    game_id = create_game(grace)
    client.post(f"/games/{game_id}/join", headers=julia["headers"])

    # HACK: We currently do not have our submit guess route complete
    #       so I update the game to be set to finished directly. Expect
    #       guesses list to be empty.
    db.table("game").update({
        "status": "finished",
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }).eq("game_id", game_id).execute()

    r = client.get(f"/games/{game_id}", headers=julia["headers"])

    assert r.status_code == 200     # game retrieved successfully
    state = r.get_json()
    assert state["status"] == "finished"    # game is marked as finished
    assert state["current_turn"] is None    # finished games have no turns
    assert len(state["answer"]) == 5        # answer is a 5 letter word

def test_get_game_as_non_participant(client, sofia, julia, create_game):
    game_id = create_game(sofia)
    r = client.get(f"/games/{game_id}", headers=julia["headers"])
    assert r.status_code == 403 # forbidden

def test_get_nonexistent_game(client, sofia):
    r = client.get(f"/games/{NONEXISTENT_ID}", headers=sofia["headers"])
    assert r.status_code == 404 # game does not exist

def test_get_game_with_bad_game_id(client, julia):
    r = client.get("/games/bad-id", headers=julia["headers"])
    assert r.status_code == 404 # games does not exist

def test_get_game_without_token(client, grace, create_game):
    game_id = create_game(grace)
    r = client.get(f"/games/{game_id}")
    assert r.status_code == 401 # unauthorized