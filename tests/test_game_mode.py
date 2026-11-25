# CMSC 447 - Shared-State Wordle
# Tests for verifing game_type

import pytest
import helpers
from datetime import datetime, timezone

FALSE_GAME_ID   = "00000000-0000-0000-0000-000000000000"
FALSE_PLAYER_ID = "00000000-0000-0000-0000-000000000000"

""" FIXTURES """

@pytest.fixture(autouse=True)
def clear_pool(db):
    (db.table("matchmaking_queue")      # DELETE
     .delete()                          # FROM matchmaking_queue
     .neq("player_id", FALSE_PLAYER_ID) # WHERE player_id != FALSE_PLAYER_ID
     .execute())

""" ROUTE CALLERS """
# Each of these is a caller for a route. Each one sends a single request and
# returns the correct response WITH NO CHECKING. This is so that intentional
# errors can be verified for consistency

def join_mm(client, player):
    return client.post("/games/match", headers=player["headers"])

def leave_mm(client, player):
    return client.delete("/games/match", headers=player["headers"])

def create_invite(client, player):
    return client.post("/games", headers=player["headers"])

def cancel_invite(client, player, game_id):
    return client.delete(f"/games/{game_id}", headers=player["headers"])

def join_invite(client, player, game_id):
    return client.post(f"/games/{game_id}/join", headers=player["headers"])

def get_state(client, player, game_id):
    return client.get(f"/games/{game_id}", headers=player["headers"])

""" INTIAL STATE HELPERS """
# Reach the database and pulls lines to verify that request worked
# as expected

def _open_game_id(player):
    game = helpers.get_open_game(player["player_id"])

    if game is not None:
        return game["game_id"]
    return FALSE_GAME_ID

def _in_same_game(player_a, player_b):
    game_a = helpers.get_open_game(player_a["player_id"])
    game_b = helpers.get_open_game(player_b["player_id"])

    if game_a is not None and game_b is not None:
        return game_a["game_id"] == game_b["game_id"]
    return False

def _get_game_type(game_id, player):
    state = helpers.get_game_state(game_id, player["player_id"])
    return state["game_type"]


""" SETUP HELPERS """
# These are used to set game variable before into a state that will impact the
# test. For example, simulating many players in queue. 

def _host_invite(client, player):
    r = create_invite(client, player)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["game_id"]

def _start_invite_game(client, host, guest):
    game_id = _host_invite(client, host)
    r = join_invite(client, guest, game_id)
    assert r.status_code == 200, r.get_json()
    assert _in_same_game(host, guest)
    return game_id

def _start_mm_game(client, player_a, player_b):
    assert join_mm(client, player_a).status_code == 202
    assert join_mm(client, player_b).status_code == 201
    assert _in_same_game(player_a, player_b)
    return _open_game_id(player_a)

""" TEST MATCH """

def test_match(client, sofia, julia):
    game_id = _start_mm_game(client, sofia, julia)
    assert _get_game_type(game_id, sofia) == "match"

def test_invite(client, sofia, julia):
    game_id = _start_invite_game(client, sofia, julia)
    assert _get_game_type(game_id, sofia) == "invite"

"""" TEST LEAVE QUEUE """

def test_match_to_invite(client, sofia, julia):
    join_mm(client, sofia)              # Sofia joins matchmaking
    create_invite(client, julia)        # Julia creates and invite
    game_id = _open_game_id(julia)      # Julia's invite code
    join_invite(client, sofia, game_id) # Sofia joins Julia's game

    assert _get_game_type(game_id, sofia) == "invite"
    assert _get_game_type(game_id, julia) == "invite"

""" TEST CANCEL INVITE """

def test_invite_to_match(client, sofia, julia):
    join_mm(client, julia)              # Julia joins matchmaking
    create_invite(client, sofia)        # Sofia creates an invite
    join_mm(client, sofia)              # Sofia joins matchmaking
    game_id = _open_game_id(julia)      # Julia and Sofia are paired

    assert _get_game_type(game_id, sofia) == "match"
    assert _get_game_type(game_id, julia) == "match"
