import uuid
import pytest
import helpers
from db import admin

@pytest.fixture
def sb():
    return admin()

@pytest.fixture
def mock_auth(monkeypatch):
    """ Mocks the Supabase Auth check in @require_user """
    class MockUser:
        def __init__(self, id):
            self.id = id
            self.is_anonymous = False

    class MockRes:
        def __init__(self, user):
            self.user = user

    class MockAuth:
        def get_user(self, token):
            # In our tests, the Bearer token IS the user_id
            return MockRes(MockUser(token))

    class MockClient:
        def __init__(self):
            self.auth = MockAuth()

    import auth
    monkeypatch.setattr(auth, "admin", lambda: MockClient())

@pytest.fixture
def seeded_game(sb):
    """ Builds a fake game and cleans it up after """
    tag = uuid.uuid4().hex[:8]
    alice, bob, gid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

    for pid, name in ((alice, "alice"), (bob, "bob")):
        admin().auth.admin.create_user({
            "id": pid,
            "email": f"{name}_{tag}@test.com",
            "password": "password123",
            "email_confirm": True,
            "user_metadata": {"username": f"{name}_{tag}"},
        })

    sb.table("word").upsert([
        {"word": "stone", "language": "eng"},
        {"word": "apple", "language": "eng"},
    ]).execute()
    sb.table("game").insert({"game_id": gid, "status": "started"}).execute()
    sb.table("answer").insert({"game_id": gid, "word": "apple", "language": "eng"}).execute()
    sb.table("plays").insert([
        {"player_id": alice, "game_id": gid, "turn_order": 1},
        {"player_id": bob, "game_id": gid, "turn_order": 2},
    ]).execute()

    yield {"game_id": gid, "alice": alice, "bob": bob}

    sb.table("game").delete().eq("game_id", gid).execute()
    admin().auth.admin.delete_user(alice)
    admin().auth.admin.delete_user(bob)

# ---------- Helper function tests ----------

def test_find_active_game(seeded_game):
    game = helpers.find_active_game(seeded_game["alice"])
    assert game["game_id"] == seeded_game["game_id"]

def test_find_active_game_none_for_stranger(sb):
    import uuid
    assert helpers.find_active_game(str(uuid.uuid4())) is None

def test_get_target_word(seeded_game):
    assert helpers.get_target_word(seeded_game["game_id"]) == "apple"

def test_insert_guess_records_row(sb, seeded_game):
    row = helpers.insert_guess(seeded_game["game_id"], seeded_game["alice"], "stone", "BBBBB")
    assert row["attempt_num"] == 1

    rows = sb.table("guess").select("*").eq("game_id", seeded_game["game_id"]).execute().data
    assert len(rows) == 1
    assert rows[0]["player_id"] == seeded_game["alice"]
    assert rows[0]["word"] == "stone"
    assert rows[0]["feedback"] == "BBBBB"

# ---------- Route tests: POST /games/guess ----------

def test_route_not_logged_in(client):
    r = client.post("/games/guess", json={"guess": "stone"})
    assert r.status_code == 401

def test_route_missing_guess(client, mock_auth):
    r = client.post("/games/guess", json={}, headers={"Authorization": "Bearer fake-user"})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Guess is required"}

def test_route_no_active_game(client, mock_auth):
    import uuid
    r = client.post("/games/guess", json={"guess": "stone"}, headers={"Authorization": f"Bearer {uuid.uuid4()}"})
    assert r.status_code == 404
    assert r.get_json() == {"error": "No active game found"}

def test_route_invalid_guess_from_team_b(client, sb, seeded_game, mock_auth, monkeypatch):
    monkeypatch.setattr(
        helpers, "evaluate_guess",
        lambda guess, target: {"valid": False, "message": "Not a valid word"},
    )
    r = client.post("/games/guess", json={"guess": "zzzzz"}, headers={"Authorization": f"Bearer {seeded_game['alice']}"})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Not a valid word"}

    rows = sb.table("guess").select("*").eq("game_id", seeded_game["game_id"]).execute().data
    assert rows == [] # Ensure nothing was saved

def test_route_valid_guess_is_inserted(client, sb, seeded_game, mock_auth, monkeypatch):
    monkeypatch.setattr(
        helpers, "evaluate_guess",
        lambda guess, target: {"valid": True, "feedback": "BBBBB"},
    )
    r = client.post("/games/guess", json={"guess": "Stone "}, headers={"Authorization": f"Bearer {seeded_game['alice']}"})
    assert r.status_code == 201
    assert r.get_json() == {
        "game_id": seeded_game["game_id"],
        "guess": "stone",
        "feedback": "BBBBB",
        "attempt_num": 1,
    }

    rows = sb.table("guess").select("*").eq("game_id", seeded_game["game_id"]).execute().data
    assert len(rows) == 1 and rows[0]["player_id"] == seeded_game["alice"]
