# CMSC 447 - Shared-State Wordle
# Tests for the matchmaking games, invite games, and switching between actions
#
#   GET     /games/<uuid:game_id>   Retrieve a game's state
#
#   POST    /games/match            Enter matchmaking pool
#   DELETE  /games/match            Exit matchmaking pool
#   
#   POST    /games                          Create invite only game
#   DELETE  /games                          Cancel an game invite
#   POST    /games/<uuid:games_id>/join     Accept a game invite

import pytest
from datetime import datetime
import helpers

FALSE_GAME_ID   = "00000000-0000-0000-0000-000000000000"
FALSE_PLAYER_ID = "00000000-0000-0000-0000-000000000000"

@pytest.fixture(autouse=True)
def dump_pool(db):
    (db.table("matchmaking_queue")      # DELETE
     .delete()                          # FROM matchmaking_queue
     .neq("player_id", FALSE_PLAYER_ID) # WHERE player_id != FALSE_PLAYER_ID
     .execute())

def match(client, player):
    return client.post("/games/match", headers=player["headers"])

def queue(db, db_rows, player, language="eng"):
    queued = db_rows(db.table("matchmaking_queue")
            .insert({"player_id": player["player_id"], "language": language})
            .execute())[0]
    return queued

def get_queued(db, db_rows):
    return [r["player_id"] for r in
            db_rows(db.table("matchmaking_queue")
                    .select("player_id")
                    .execute())]

def get_timestamp(db, db_rows, player):
    timestamp = (db_rows(db.table("matchmaking_queue")
                         .select("joined_at")
                         .eq("player_id", player["player_id"])
                         .execute()))
    return datetime.fromisoformat(timestamp[0]["joined_at"])

def games_exists(db, db_rows, game_id):
    game = (db_rows(db.table("game")
                    .select("game_id")
                    .eq("game_id", game_id)
                    .execute()))
    return game != []

def set_language(db, player, language):
    (db.table("player")
     .update({"language": language})
     .eq("player_id", player["player_id"])
     .execute())

""" QUEUE TESTS """

# Verify that the first player in the queue waits
def test_first_player_in_queue_waits(client, db, db_rows, sofia):
    r = match(client, sofia)    # sofia enters matchmaking

    assert r.status_code == 202                                 # No players found but request sucessful
    assert r.get_json() == {"queued": True, "game_id": None}    # JSON reports sofia as added to queue
    assert get_queued(db, db_rows) == [sofia["player_id"]]      # sofia appears in the match_making table
    assert helpers.get_open_game(sofia["player_id"]) is None    # No open game was created for sofia

# Verify that the second in the queue is joined with first player
def test_second_player_in_queue_joins(client, db, db_rows, sofia, grace):
    first  = match(client, sofia)    # sofia enters matchmaking
    second = match(client, grace)

    assert first.status_code  == 202 # joined queue
    assert second.status_code == 201 # found match
    assert get_queued(db, db_rows) == [] # nobody in queue
    assert helpers.get_open_game(sofia["player_id"]) is not None
    assert helpers.get_open_game(grace["player_id"]) is not None

# Verify that if three players are in the queue oldest two are paired
def test_third_player_in_queue_waits(client, db, db_rows, sofia, grace, julia):
    # Inserting players directly into the tables skips the intial matchmaking
    # attempt therefore, Sofia won't be matched with Grace
    queue(db, db_rows, sofia)
    queue(db, db_rows, grace)
    r = match(client, julia)

    assert r.status_code == 201 # Found match
    assert get_queued(db, db_rows) == [grace["player_id"]]
    assert helpers.get_open_game(sofia["player_id"]) is not None # Paired with Julia
    assert helpers.get_open_game(julia["player_id"]) is not None # Paired with Sofia
    assert helpers.get_open_game(grace["player_id"]) is None # Continues to wait

# Verify that oncea match is made the game is set to start and exists in the game row
def test_paired_game_updated_to_start(client, sofia, grace, db, db_rows):
    first = match(client, sofia)
    assert first.status_code == 202 # Added to queue
    assert helpers.get_open_game(sofia["player_id"]) is None # No game started

    second = match(client, grace)
    assert second.status_code == 201 # Found Match

    sofia_game = helpers.get_open_game(sofia["player_id"])  # Sofia should be in an open game
    grace_game = helpers.get_open_game(grace["player_id"])  # Grace should be in an open game
    assert sofia_game is not None
    assert grace_game is not None

    assert games_exists(db, db_rows, sofia_game["game_id"]) # Verify game exists in game row
    assert sofia_game["game_id"] == grace_game["game_id"]   # Sofia and Grace are in the same game
    assert sofia_game["status"] == "started"
    assert grace_game["status"] == "started"

# Verify that leaving the queue updates your joined_at time
def test_leaving_queue_removes_timestamp(client, sofia, db, db_rows):
    match(client, sofia)                                    # Enter queue
    first = get_timestamp(db, db_rows, sofia)               # Time of first join
    client.delete("/games/match", headers=sofia["headers"]) # Exit queue
    match(client, sofia)                                    # Rejoin queue
    second = get_timestamp(db, db_rows, sofia)              # Time of sceond join

    assert first < second
    assert first != second

# Verify a player can leave the queue
def test_leave_queue(client, sofia, db, db_rows):
    join = match(client, sofia)
    assert join.status_code == 202
    leave = client.delete("/games/match", headers=sofia["headers"])
    assert leave.status_code == 204
    assert get_queued(db, db_rows) == []

# Verify a player can rejoin the queue after leaving
def test_rejoin_queue(client, sofia, grace, db, db_rows):
    sofia_join = match(client, sofia)
    assert sofia_join.status_code == 202

    sofia_leave = client.delete("/games/match", headers=sofia["headers"])
    assert sofia_leave.status_code == 204
    assert get_queued(db, db_rows) == []

    sofia_rejoin = match(client, sofia)
    assert sofia_rejoin.status_code == 202

    grace_join = match(client, grace)
    assert grace_join.status_code == 201

    assert get_queued(db, db_rows) == []

# TODO: Verify game language is set to players preference

# TODO: Verify two player of different language do not get paired together

