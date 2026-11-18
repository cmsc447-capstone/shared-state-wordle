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

def c_get_game_state(client, player, game_id):
    r = client.get(f"/games/{game_id}", headers=player["headers"])
    assert r.status_code == 200, r.get_json()
    return r

def c_join_matchmake(client, player):
    r = client.post("/games/match", headers=player["headers"])
    assert r.status_code in (201, 202), r.get_json()
    return r

def c_leave_matchmake(client, player):
    r = client.delete("/games/match", headers=player["headers"])
    assert r.status_code == 204, r.get_json()

def c_create_invite_game(client, player):
    r = client.post("/games", headers=player["headers"])
    assert r.status_code == 201, r.get_json()
    return r

def c_cancel_invite_game(client, player):
    r = client.delete("/games", headers=player["headers"])
    assert r.status_code == 204, r.get_json()

def c_join_invite_game(client, player, game_id):
    r = client.post(f"/games/{game_id}/join", headers=player["headers"])
    assert r.status_code == 200, r.get_json()
    return r

""" TEST HELPERS """

def _tickets(player_id, db, db_rows):
    res = (db.table("matchmaking_queue")
           .select("*")
           .eq("player_id", player_id)
           .execute())
    return db_rows(res)

def _inject_into_queue(player, db):
    language = helpers.get_player_language(player["player_id"])
    (db.table("matchmaking_queue")
     .insert({"player_id": player["player_id"], "language": language})
     .execute())

def _get_queued(db, db_rows):
    return [r["player_id"] for r in
            db_rows(db.table("matchmaking_queue")
                    .select("player_id")
                    .order("joined_at")
                    .execute())]

def _in_same_game(player_a, player_b):
    game_a = helpers.get_open_game(player_a["player_id"])
    game_b = helpers.get_open_game(player_b["player_id"])

    if game_a is not None and game_b is not None:
        return game_a["game_id"] == game_b["game_id"]
    return False

""" MATCHMAKING ROUTES TEST """

def test_first_player_in_queue(client, sofia):
    r = c_join_matchmake(client, sofia)

    assert r.get_json() == {"queued": True, "game_id": None}
    assert helpers.in_queue(sofia["player_id"])

def test_second_player_in_queue(client, sofia, julia):
    first = c_join_matchmake(client, sofia)

    assert first.status_code == 202
    assert first.get_json() == {"queued": True, "game_id": None}

    second = c_join_matchmake(client, julia)

    julia_game = helpers.get_open_game(julia["player_id"])
    sofia_game = helpers.get_open_game(sofia["player_id"])

    assert julia_game is not None
    assert sofia_game is not None

    assert second.status_code == 201
    assert second.get_json() == {"queued": False, "game_id": julia_game["game_id"]}

    assert _in_same_game(sofia, julia)

def test_thrid_player_in_queue(client, sofia, julia, grace, db, db_rows):
    _inject_into_queue(sofia, db) # FIRST
    _inject_into_queue(julia, db) # SECOND

    assert _get_queued(db, db_rows) == [sofia["player_id"], julia["player_id"]]

    r = c_join_matchmake(client, grace)
    assert r.status_code == 201

    assert _get_queued(db, db_rows) == [julia["player_id"]] # Only Julia waits

    assert _in_same_game(sofia, grace)

def test_lave 

""" HELPER TESTS """
# Helpers aren't completly tested here. The tests in this program
# focus on testing the routes. Tests are preformed on the individual
# helpers when creating the behaviour on the routes is too challenging

def test_in_queue_helper(client, sofia):
    assert helpers.in_queue(sofia["player_id"]) == False
    c_join_matchmake(client, sofia)
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

    # TODO: RACE