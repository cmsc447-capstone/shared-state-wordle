# CMSC447 - Shared-State Wordle
# The following test cover changes to match making
# it covers both invite game sessions and matched
# games assigned by the server. As well as the
# ability to leave to pool / cancel a match
#   POST    /games
#   POST    /games/<game_id>/join
#   GET     /games/<game_id>

import uuid
import pytest
import helpers
from datetime import datetime, timezone

NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"

@pytest.fixture(autouse=True)
def empty_pool(db):
    (db.table("game")           # DELETE
     .delete()                  # FROM game
     .eq("status", "waiting")   # WHERE status = 'waiting'
     .eq("mode", "match")       #   AND mode = 'match'
     .execute())

def set_language(db, player, language):
    (db.table("player")                 # UPDATE language -> language
     .update({"language": language})    # FROM player
     .eq("player_id", player["id"])     # WHERE player_id = player_id
     .execute())

def test_first_player_in_pool(client, grace, db, db_rows):
    r = client.post("/games/match", headers=grace["headers"])

    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "waiting"  # new games wait for match to be found
    assert body["matched"] is False     # new games are not initially matched

    # Verify that the game mode from games created
    # from players looking for matches is match
    game = db_rows(db.table("game")
                   .select("mode")
                   .eq("game_id", body["game_id"])
                   .execute())
    assert game[0]["mode"] == "match"

# test grace is the first player to join the pool
# julia joins second and is matched with grace
def test_second_player_in_pool(client, grace, julia):
    first = client.post("/games/match", headers=grace["headers"]).get_json()
    r = client.post("/games/match", headers=julia["headers"])

    assert r.status_code == 200 # P2 successfully joins game
    body = r.get_json()
    assert body["game_id"] == first["game_id"]      # game joined by P2 matches game_id of P1
    assert body["status"] == "started"              # Once two players are in a game status -> started
    assert body["matched"] is True                  # the game is matched

# test that two players with different language settings
# are not matched by the server. Invite cross lang: OK
def test_different_language(client, grace, sofia, db):
    set_language(db, sofia, "esp")
    first = client.post("/games/match", headers=sofia["headers"]).get_json()
    r = client.post("/games/match", headers=grace["headers"])

    assert r.status_code == 201                         # grace waits
    assert r.get_json()["game_id"] != first["game_id"]  # game_id should not match

# the language should match both players, we use spanish
# because english is default
def test_game_language(client, julia, grace, db):
    set_language(db, grace, "esp")
    set_language(db, julia, "esp")
    first = client.post("/games/match", headers=grace["headers"]).get_json()
    r = client.post("/games/match", headers=julia["headers"])
    state = client.get(f"/games/{first["game_id"]}", headers=julia["headers"]).get_json()

    assert state["language"] == "esp"                   # language matches both players "esp"
    assert first["game_id"] == r.get_json()["game_id"]  # both players matched

def test_matched_oldest_game(client, julia, sofia, grace):
    first  = helpers.create_game(julia["id"], "eng", mode="match")
    helpers.create_game(sofia["id"], "eng", mode="match")

    r = client.post("/games/match", headers=grace["headers"])

    assert r.get_json()["game_id"] == first["game_id"]  # grace is matched with julia's game

# test matchmaking ingnores invite games
def test_invite_games_protected(client, grace, julia):
    invite = helpers.create_game(grace["id"], "eng", mode="invite")
    r = client.post("/games/match", headers=julia["headers"])

    assert r.status_code == 201
    assert r.get_json()["status"] == "waiting"
    assert invite["status"] == "waiting"

# test cannot doubly enter matchmaking
def test_match_while_in_game(client, sofia):
    client.post("/games/match", headers=sofia["headers"])       # can enter matchmaking
    r = client.post("/games/match", headers=sofia["headers"])   # cannot enter while already waiting for matchmaking

    assert r.status_code == 409
    
# TODO: test cannot invite while in matchmaking
def test_invite_while_in_matchmaking(client, sofia):
    client.post("/games/match", headers=sofia["headers"])                         # enter matchmaking
    r = client.post("/games", json={"language": "eng"}, headers=sofia["headers"]) # attempt to create invite

    assert r.status_code == 409

# test invite games match host language
def test_invite_in_host_language(client, julia, sofia, create_game, db):
    set_language(db, sofia, "esp")                                                              # sofia perfers spanish
    set_language(db, julia, "eng")                                                              # julia perfers english
    host = client.post("/games", json={}, headers=sofia["headers"])                             # sofia makes a game
    assert host.status_code == 201                                                              # sofia waits for julia
    assert host.get_json()["language"] == "esp"                                                 # check game is in spanish
    goer = client.post(f"/games/{host.get_json()["game_id"]}/join", headers=julia["headers"])   # julia joins sofia's game
    assert goer.status_code == 200                                                              # julia joined
    assert host.get_json()["language"] == "esp"                                                 # game still in spanish


# test host can cancel matchmaking
def test_cancel_matchmaking(client, julia, sofia):
    make    = client.post("/games/match", headers=julia["headers"])                             # julia enters matchmaking
    assert make.status_code == 201                                                              # julia waits
    delete  = client.delete(f"/games/{make.get_json()["game_id"]}", headers=julia["headers"])   # julia leaves matchmaking
    assert delete.status_code == 204                                                            # deleted successfully

    r       = client.post("/games/match", headers=sofia["headers"])                             # sofia enters matchmaking
    assert r.status_code == 201                                                                 # sofia waits

# test canceled matchmaking deletes game from game table
def test_game_deleted(client, grace, db, db_rows):
    r = client.post("/games/match", headers=grace["headers"])
    client.delete(f"/games/{r.get_json()["game_id"]}", headers=grace["headers"])

    game = db_rows(db.table("game")
                   .select("game_id")
                   .eq("game_id", r.get_json()["game_id"])
                   .execute())
    assert game == []   # found no game in game table with that game_id

# test player in pool cannot join a game from invite
def test_matchmaking_join_invite(client, grace, sofia, create_game):
    mm = client.post("/games/match", headers=sofia["headers"])   # sofia joins matchmaking
    assert mm.status_code == 201                                 # sofia waits in matchmaking
    game_id = create_game(grace)                                # grace creates an invite game
    r = client.post(f"/games/{game_id}/join", headers=sofia["headers"]) # sofia joins 
    assert r.status_code == 409


# TODO: test players can enter matchmaking after canceling
# TODO: test players can invite after canceling 
# TODO: test started game cannot be cancelled
# TODO: test only host can cancel a game
# TODO: test canceling a non-existent game isn't allowed
# TODO: test canceling without a token isn't allowed