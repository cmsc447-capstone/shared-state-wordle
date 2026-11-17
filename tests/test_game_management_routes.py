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

def get_queued(db, db_rows):
    return [r["player_id"] for r in
            db_rows(db.table("matchmaking_queue")
                    .select("player_id")
                    .execute())]

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

# TODO: Verify that the second in the queue is joined with first player

# TODO: Verify that if three players are in the queue oldest two are paired

# TODO: Verify that oncea match is made the game is set to start and exists in the game row

# TODO: Verify that a player who leaves and joins the queue has different timestamp

# TODO: Verify that a failed paring keeps the original player timestamps

# TODO: Verify a player can leave the queue

# TODO: Verify a player can rejoin the queue after leaving

# TODO: Verify game language is set to players preference

# TODO: Verify two player of different language do not get paired together

