# CMSC 447 - Shared-State Wordle
# Tests for the matchmaking games, invite games, and switching between actions
#
#   POST    /games/match            Enter matchmaking pool
#   DELETE  /games/match            Exit matchmaking pool

import pytest
import helpers
from datetime import datetime

FALSE_GAME_ID   = "00000000-0000-0000-0000-000000000000"
FALSE_PLAYER_ID = "00000000-0000-0000-0000-000000000000"

@pytest.fixture(autouse=True)
def clear_pool(db):
    (db.table("matchmaking_queue")
     .delete()
     .neq("player_id", FALSE_PLAYER_ID)
     .execute())

def get_game_state(client, player, game_id):
    r = client.get(f"/games/{game_id}", headers=player["headers"])
    assert r.status_code == 200, r.get_json()
    return r.get_json()

def join_matchmake(client, player):
    r = client.post("/games/match", headers=player["headers"])
    assert r.status_code in (201, 202), r.get_json()
    return r.get_json()

def leave_matchmake(client, player):
    r = client.delete("/games/match", headers=player["headers"])
    assert r.status_code == 204, r.get_json()

def create_invite_game(client, player):
    r = client.post("/games", headers=player["headers"])
    assert r.status_code == 201, r.get_json()
    return r.get_json()

def cancel_invite_game(client, player):
    r = client.delete("/games", headers=player["headers"])
    assert r.status_code == 204, r.get_json()

def join_invite_game(client, player, game_id):
    r = client.post(f"/games/{game_id}/join", headers=player["headers"])
    assert r.status_code == 200, r.get_json()
    return r.get_json()

""" TEST HELPERS """

def _tickets(player_id, db, db_rows):
    res = (db.table("matchmaking_queue")
           .select("*")
           .eq("player_id", player_id)
           .execute())
    return db_rows(res)

# First player can enter queue

# First player waits in queue

# First player in queue returns status 202

# First player in queue is written to matchmaking table

def test_in_queue_helper(client, sofia):
    assert helpers.in_queue(sofia["player_id"]) == False
    join_matchmake(client, sofia)
    assert helpers.in_queue(sofia["player_id"]) == True

def test_join_queue_normal(sofia, db, db_rows):
    helpers.join_queue(sofia["player_id"], "eng")
    ticket = _tickets(sofia["player_id"], db, db_rows)

    assert ticket[0]["player_id"] == sofia["player_id"]
    assert ticket[0]["language"]  == "eng"
    assert ticket[0]["joined_at"] is not None

def test_join_queue_double_join(sofia, db, db_rows):
    helpers.join_queue(sofia["player_id"], "eng")
    original = _tickets(sofia["player_id"], db, db_rows)

    helpers.join_queue(sofia["player_id"], language="end")
    duplicate = _tickets(sofia["player_id"], db, db_rows)

    assert len(_tickets(sofia["player_id"], db, db_rows)) == 1
    assert original[0]["joined_at"] == duplicate[0]["joined_at"]

def test_join_preserves_timestamp(sofia, db, db_rows):
    original = "2026-01-01T00:00:00+00:00"
    helpers.join_queue(sofia["player_id"], "eng", joined_at=original)

    assert original == _tickets(sofia["player_id"], db, db_rows)[0]["joined_at"]

def test_first_player_in_queue(client, sofia):
    body = join_matchmake(client, sofia)

    assert body == {"queued": True, "game_id": None}
    assert helpers.in_queue(sofia["player_id"])