# CMSC447 - Shared-State Wordle
# The following test cover all game managment routes
#   POST    /games
#   POST    /games/<game_id>/join
#   GET     /games/<game_id>

import uuid
from datetime import datetime, timezone

NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"

# POST /games

def test_create_game(client, avery):
    r = client.post("/games", json={"language": "eng"}, headers=avery["headers"])

    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "waiting"  # waiting for second player to join
    assert body["language"] == "eng"    # langauge matches perferred langauge
    uuid.UUID(body["game_id"])          # verifies a valid UUID
    assert "answer" not in body         # game not finished so no answer should be present

def test_create_game_writes_plays_and_answer(client, avery, db, db_rows):
    r = client.post("/games", json={"language": "eng"}, headers=avery["headers"])
    game_id = r.get_json()["game_id"]

    plays = db_rows(db.table("plays").select("*").eq("game_id", game_id).execute())
    assert len(plays) == 1                      # So far only avery plays in this game
    assert plays[0]["player_id"] == avery["id"] # avery ID matches player id in plays as player 1
    assert plays[0]["turn_order"] == 1          # avery has the first turn

    answer = db_rows(db.table("answer").select("*").eq("game_id", game_id).execute())
    assert len(answer) == 1                 # this game should only have one answer
    assert answer[0]["language"] == "eng"   # answer language should match player language
    assert len(answer[0]["word"]) == 5      # lenght of answer word should be 5 letters 