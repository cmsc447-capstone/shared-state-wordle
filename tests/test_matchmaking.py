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
    return r

def c_cancel_invite_game(client, player, game_id):
    r = client.delete(f"/games/{game_id}", headers=player["headers"])
    assert r.status_code == 204, r.get_json()

def c_join_invite_game(client, player, game_id):
    r = client.post(f"/games/{game_id}/join", headers=player["headers"])
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

def _get_open(player):
    game = helpers.get_open_game(player["player_id"])

    if game is not None:
        return game["game_id"]
    return FALSE_GAME_ID

def _create_and_join(client, player_a, player_b):
    c_create_invite_game(client, player_a)
    game_id = _get_open(player_a)
    c_join_invite_game(client, player_b, game_id)
    return game_id

def _queue_and_pair(client, player_a, player_b):
    c_join_matchmake(client, player_a)
    c_join_matchmake(client, player_b)
    assert _in_same_game(player_a, player_b)
    game = helpers.get_open_game(player_a["player_id"])

    if game is not None:
        return game["game_id"]
    return FALSE_GAME_ID

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

def test_leave_queue_normal(client, sofia, db, db_rows):
    c_join_matchmake(client, sofia)
    c_leave_matchmake(client, sofia)

    assert _get_queued(db, db_rows) == []

def test_leave_queue_and_rejoin(client, sofia, db, db_rows):
    c_join_matchmake(client, sofia)
    c_leave_matchmake(client, sofia)
    c_join_matchmake(client, sofia)

    assert _get_queued(db, db_rows) == [sofia["player_id"]]

def test_leave_and_rejoin_still_pairable(client, sofia, julia, db, db_rows):
    _inject_into_queue(sofia, db)
    _inject_into_queue(julia, db)
    c_leave_matchmake(client, sofia)

    assert _get_queued(db, db_rows) == [julia["player_id"]]

    r = c_join_matchmake(client, sofia)
    assert r.status_code == 201

    assert _in_same_game(sofia, julia)

def test_leave_queue_resets_timestamp(client, sofia, db, db_rows):
    original = "2026-01-01T00:00:00+00:00"
    helpers.join_queue(sofia["player_id"], "eng", original)

    assert original == _tickets(sofia["player_id"], db, db_rows)[0]["joined_at"]

    c_leave_matchmake(client, sofia)
    c_join_matchmake(client, sofia)

    assert _tickets(sofia["player_id"], db, db_rows)[0]["joined_at"] != original

def test_leave_mm_safe_to_call_on_unqueued_players(client, sofia, db, db_rows):
    assert _get_queued(db, db_rows) == []
    c_leave_matchmake(client, sofia) # 204 checked in c_leave_matchmake
    assert _get_queued(db, db_rows) == []

""" INVITE ROUTES TEST """

def test_create_invite_game(client, sofia):
    assert _get_open(sofia) == FALSE_GAME_ID
    c_create_invite_game(client, sofia)

    invite = _get_open(sofia)
    assert invite != FALSE_GAME_ID

def test_cancel_invite_game(client, sofia):
    c_create_invite_game(client, sofia)
    game_id = _get_open(sofia)
    c_cancel_invite_game(client, sofia, game_id)
    assert _get_open(sofia) == FALSE_GAME_ID

def test_join_invite_game(client, sofia, grace):
    c_create_invite_game(client, sofia)
    game_id = _get_open(sofia)
    c_join_invite_game(client, grace, game_id)

    assert _in_same_game(sofia, grace)

def test_create_two_invtes(client, sofia):
    first = c_create_invite_game(client, sofia)
    assert first.status_code == 201
    game_id = _get_open(sofia)

    second  = c_create_invite_game(client, sofia)
    assert second.status_code == 409

    assert game_id == _get_open(sofia)

def test_create_invite_leaves_mm(client, sofia, db, db_rows):
    c_join_matchmake(client, sofia)
    assert _get_queued(db, db_rows) == [sofia["player_id"]]

    r = c_create_invite_game(client, sofia)
    assert r.status_code == 201

    assert _get_queued(db, db_rows) == []

def test_create_invite_after_leaving_mm_is_joinable(client, sofia, julia):
    c_join_matchmake(client, sofia)
    c_create_invite_game(client, sofia)
    game_id = _get_open(sofia)
    c_join_invite_game(client, julia, game_id)

    assert _in_same_game(sofia, julia)

def test_invite_unjoinable_when_entering_mm(client, sofia, julia):
    c_create_invite_game(client, sofia)
    game_id = _get_open(sofia)
    c_join_matchmake(client, sofia)

    r = c_join_invite_game(client, julia, game_id)
    assert r.status_code == 404
    assert _in_same_game(sofia, julia) == False

def test_cancel_invite_as_non_host(client, sofia, julia):
    c_create_invite_game(client, sofia)
    game_id = _get_open(sofia)

    r = client.delete(f"/games/{game_id}", headers=julia["headers"])
    assert r.status_code == 403

def test_cannot_cancel_started_invite_game(client, sofia, julia):
    game_id = _create_and_join(client, sofia, julia)

    s = client.delete(f"/games/{game_id}", headers=julia["headers"])
    assert s.status_code == 403

    j = client.delete(f"/games/{game_id}", headers=sofia["headers"])
    assert j.status_code == 409

    assert _get_open(sofia) == game_id

def test_two_players_accept_invite(client, sofia, julia, grace):
    c_create_invite_game(client, sofia)
    game_id = _get_open(sofia)

    first = c_join_invite_game(client, julia, game_id)
    assert first.status_code == 200

    second = c_join_invite_game(client, grace, game_id)
    assert second.status_code == 409

    assert _in_same_game(sofia, julia)
    assert _in_same_game(sofia, grace) == False

def test_cannot_join_mm_with_started_invite_game(client, sofia, julia):
    _create_and_join(client, sofia, julia)

    assert _in_same_game(sofia, julia)

    s = client.post("/games/match", headers=sofia["headers"])
    assert s.status_code == 409
    j = client.post("/games/match", headers=julia["headers"])
    assert j.status_code == 409

def test_cannot_join_mm_with_started_mm_game(client, sofia, julia):
    _queue_and_pair(client, sofia, julia)

    s = client.post("/games/match", headers=sofia["headers"])
    assert s.status_code == 409
    j = client.post("/games/match", headers=julia["headers"])
    assert j.status_code == 409

def test_cannot_accept_invite_with_started_invite_game(client, sofia, julia, grace):
    _create_and_join(client, sofia, julia)
    c_create_invite_game(client, grace)
    game_id = _get_open(grace)

    s = client.post(f"/games/{game_id}/join", headers=sofia["headers"])
    assert s.status_code == 409
    j = client.post(f"/games/{game_id}/join", headers=julia["headers"])
    assert j.status_code == 409

def test_cannot_accept_invite_with_started_mm_game(client, sofia, julia, grace):
    _queue_and_pair(client, sofia, julia)
    c_create_invite_game(client, grace)
    game_id = _get_open(grace)

    s = client.post(f"/games/{game_id}/join", headers=sofia["headers"])
    assert s.status_code == 409
    j = client.post(f"/games/{game_id}/join", headers=julia["headers"])
    assert j.status_code == 409

def test_cannot_create_invite_with_started_mm_game(client, sofia, julia):
    _queue_and_pair(client, sofia, julia)

    s = client.post("/games", headers=sofia["headers"])
    j = client.post("/games", headers=julia["headers"])

    assert s.status_code == 409
    assert j.status_code == 409

def test_cannot_create_invite_with_started_invite_game(client, sofia, julia):
    _create_and_join(client, sofia, julia)

    s = client.post("/games", headers=sofia["headers"])
    j = client.post("/games", headers=julia["headers"])

    assert s.status_code == 409
    assert j.status_code == 409

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