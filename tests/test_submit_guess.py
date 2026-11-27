import pytest
import helpers

# ---------- ROUTE CALLERS ----------
# Sends a single request and returns the response

def submit_guess(client, player, word):
    return client.post(
        "/games/guess", 
        json={"guess": word}, 
        headers=player["headers"]
    )

# ---------- STATE HELPERS ----------
# Reach the database to verify the request worked

def _get_guesses(db, db_rows, game_id):
    res = (db.table("guess")
           .select("*")
           .eq("game_id", game_id)
           .execute())
    return db_rows(res)

# ---------- HELPER FUNCTION TESTS ----------

def test_find_active_game(seeded_game, sofia):
    game = helpers.find_active_game(sofia["player_id"])
    assert game["game_id"] == seeded_game

def test_get_target_word(seeded_game):
    assert helpers.get_target_word(seeded_game) == "apple"

def test_insert_guess_records_row(seeded_game, sofia, db, db_rows):
    row = helpers.insert_guess(seeded_game, sofia["player_id"], "stone", "BBBBB")
    assert row["attempt_num"] == 1

    rows = _get_guesses(db, db_rows, seeded_game)
    assert len(rows) == 1
    assert rows[0]["player_id"] == sofia["player_id"]
    assert rows[0]["word"] == "stone"
    assert rows[0]["feedback"] == "BBBBB"

# ---------- ROUTE TESTS ----------

def test_route_not_logged_in(client):
    r = client.post("/games/guess", json={"guess": "stone"})
    assert r.status_code == 401

def test_route_missing_guess(client, sofia):
    r = submit_guess(client, sofia, "")
    assert r.status_code == 400
    assert r.get_json() == {"error": "Guess is required"}

def test_route_no_active_game(client, sofia):
    r = submit_guess(client, sofia, "stone")
    assert r.status_code == 404
    assert r.get_json() == {"error": "No active game found"}

def test_route_invalid_guess_from_team_b(client, seeded_game, sofia, db, db_rows, monkeypatch):
    monkeypatch.setattr(
        helpers, "evaluate_guess",
        lambda guess, target: {"valid": False, "message": "Not a valid word"},
    )
    r = submit_guess(client, sofia, "zzzzz")
    
    assert r.status_code == 400
    assert r.get_json() == {"error": "Not a valid word"}

    # Verify nothing was saved to the DB
    assert len(_get_guesses(db, db_rows, seeded_game)) == 0

def test_route_valid_guess_is_inserted(client, seeded_game, sofia, db, db_rows, monkeypatch):
    monkeypatch.setattr(
        helpers, "evaluate_guess",
        lambda guess, target: {"valid": True, "feedback": "BBBBB"},
    )
    
    # "Stone " tests that the route trims and lowercases
    r = submit_guess(client, sofia, "Stone ")
    
    assert r.status_code == 201
    assert r.get_json() == {
        "game_id": seeded_game,
        "guess": "stone",
        "feedback": "BBBBB",
        "attempt_num": 1,
    }

    # Verify the DB actually recorded it
    rows = _get_guesses(db, db_rows, seeded_game)
    assert len(rows) == 1 
    assert rows[0]["player_id"] == sofia["player_id"]
