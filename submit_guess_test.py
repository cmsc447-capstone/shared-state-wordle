import uuid
from datetime import datetime, timezone

import pytest

import helpers
from db import admin
from flask_server import app


# ---------- setup (fixtures) ----------

# Gives each test a database connection
@pytest.fixture
def sb():
    return admin()


# Builds a fake game before each test and deletes it afterward.
# Two players (alice goes first, bob second). The secret answer is "apple".
@pytest.fixture
def seeded_game(sb):
    tag = uuid.uuid4().hex[:8]  # random suffix so usernames never collide
    alice, bob, gid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

    # Words must exist in the word table before they can be used as answers or guesses
    sb.table("word").upsert([{"word": "stone"}, {"word": "apple"}]).execute()
    sb.table("users").insert([
        {"user_id": alice, "username": f"alice_{tag}"},
        {"user_id": bob, "username": f"bob_{tag}"},
    ]).execute()
    sb.table("game").insert({"game_id": gid, "status": "started"}).execute()
    sb.table("answer").insert({"game_id": gid, "word": "apple"}).execute()
    sb.table("plays").insert([
        {"user_id": alice, "game_id": gid, "turn_order": 1},
        {"user_id": bob, "game_id": gid, "turn_order": 2},
    ]).execute()

    yield {"game_id": gid, "alice": alice, "bob": bob}

    # Cleanup: deleting the game also removes its plays, answer, and guesses
    sb.table("game").delete().eq("game_id", gid).execute()
    sb.table("users").delete().in_("user_id", [alice, bob]).execute()


# A fake browser that can call the Flask routes
@pytest.fixture
def client():
    app.secret_key = app.secret_key or "test"
    return app.test_client()


# Pretend this user is logged in by putting their id in the session
def login_as(client, user_id):
    with client.session_transaction() as s:
        s["user_id"] = user_id


# ---------- helper function tests ----------

# A player in a started game should get that game back
def test_find_active_game_returns_game(seeded_game):
    game = helpers.find_active_game(seeded_game["alice"])
    assert game["game_id"] == seeded_game["game_id"]


# Both players should land in the same game
def test_find_active_game_works_for_both_players(seeded_game):
    a = helpers.find_active_game(seeded_game["alice"])
    b = helpers.find_active_game(seeded_game["bob"])
    assert a["game_id"] == b["game_id"] == seeded_game["game_id"]


# A user who is in no game gets None
def test_find_active_game_none_for_stranger(sb):
    assert helpers.find_active_game(str(uuid.uuid4())) is None


# A finished game no longer counts as active
def test_find_active_game_ignores_finished(sb, seeded_game):
    sb.table("game").update({
        "status": "finished",
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }).eq("game_id", seeded_game["game_id"]).execute()
    assert helpers.find_active_game(seeded_game["alice"]) is None


# The target word should be the answer we set up ("apple")
def test_get_target_word(seeded_game):
    assert helpers.get_target_word(seeded_game["game_id"]) == "apple"


# A game that doesn't exist has no target word
def test_get_target_word_none_for_unknown_game(sb):
    assert helpers.get_target_word(str(uuid.uuid4())) is None


# Inserting a guess should save exactly one row with the right values
def test_insert_guess_records_row(sb, seeded_game):
    row = helpers.insert_guess(seeded_game["game_id"], seeded_game["alice"], "stone", "BBBBB")
    assert row["attempt_num"] == 1

    rows = sb.table("guess").select("*").eq("game_id", seeded_game["game_id"]).execute().data
    assert len(rows) == 1
    assert rows[0]["user_id"] == seeded_game["alice"]
    assert rows[0]["word"] == "stone"
    assert rows[0]["feedback"] == "BBBBB"


# Each new guess in the same game gets the next attempt number
def test_attempt_num_increments(seeded_game):
    gid = seeded_game["game_id"]
    r1 = helpers.insert_guess(gid, seeded_game["alice"], "stone", "BBBBB")
    r2 = helpers.insert_guess(gid, seeded_game["bob"], "stone", "BBBBB")
    assert (r1["attempt_num"], r2["attempt_num"]) == (1, 2)


# ---------- route tests: POST /games/guess ----------
# These match the response table shared with Team C.

# 401: no login session
def test_route_not_logged_in(client):
    r = client.post("/games/guess", json={"guess": "stone"})
    assert r.status_code == 401
    assert r.get_json() == {"message": "Not logged in"}


# 400: logged in but no guess in the request
def test_route_missing_guess(client):
    login_as(client, str(uuid.uuid4()))
    r = client.post("/games/guess", json={})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Guess is required"}


# 404: logged in but not in any active game
def test_route_no_active_game(client):
    login_as(client, str(uuid.uuid4()))
    r = client.post("/games/guess", json={"guess": "stone"})
    assert r.status_code == 404
    assert r.get_json() == {"error": "No active game found"}


# 500: the game exists but has no answer row (should not happen normally)
def test_route_game_has_no_answer(client, sb, seeded_game):
    sb.table("answer").delete().eq("game_id", seeded_game["game_id"]).execute()
    login_as(client, seeded_game["alice"])
    r = client.post("/games/guess", json={"guess": "stone"})
    assert r.status_code == 500
    assert r.get_json() == {"error": "Game has no answer"}


# 400: Team B says the guess is invalid. We fake Team B's answer here,
# and check that nothing was saved to the database.
def test_route_invalid_guess_from_team_b(client, sb, seeded_game, monkeypatch):
    monkeypatch.setattr(
        helpers, "evaluate_guess",
        lambda guess, target: {"valid": False, "error": "Not a valid word"},
    )
    login_as(client, seeded_game["alice"])
    r = client.post("/games/guess", json={"guess": "zzzzz"})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Not a valid word"}

    rows = sb.table("guess").select("*").eq("game_id", seeded_game["game_id"]).execute().data
    assert rows == []   # nothing stored for an invalid guess


# 201: Team B says valid, so the guess is saved and returned.
# The input "Stone " also checks that the route trims spaces and lowercases.
def test_route_valid_guess_is_inserted(client, sb, seeded_game, monkeypatch):
    monkeypatch.setattr(
        helpers, "evaluate_guess",
        lambda guess, target: {"valid": True, "feedback": "BBBBB"},
    )
    login_as(client, seeded_game["alice"])
    r = client.post("/games/guess", json={"guess": "Stone "})
    assert r.status_code == 201
    assert r.get_json() == {
        "game_id": seeded_game["game_id"],
        "guess": "stone",
        "feedback": "BBBBB",
        "attempt_num": 1,
    }

    rows = sb.table("guess").select("*").eq("game_id", seeded_game["game_id"]).execute().data
    assert len(rows) == 1 and rows[0]["user_id"] == seeded_game["alice"]


# The route should hand Team B the cleaned guess and the game's secret word
def test_route_passes_target_word_to_team_b(client, seeded_game, monkeypatch):
    seen = {}

    def fake(guess, target):
        seen["guess"], seen["target"] = guess, target
        return {"valid": True, "feedback": "BBBBB"}

    monkeypatch.setattr(helpers, "evaluate_guess", fake)
    login_as(client, seeded_game["alice"])
    client.post("/games/guess", json={"guess": "stone"})
    assert seen == {"guess": "stone", "target": "apple"}
