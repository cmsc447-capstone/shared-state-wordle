import os
from dotenv import load_dotenv
load_dotenv(".env.test")
os.environ["SUPABASE_URL"] = os.environ.get("SUPABASE_TEST_URL", "http://127.0.0.1:54321")
os.environ["SUPABASE_KEY"] = os.environ.get("SUPABASE_TEST_KEY", "")

import pytest
import psycopg2
from supabase import create_client


@pytest.fixture(scope="session")
def sb():
    """Session-scoped Supabase client pointed at the local test DB."""
    return create_client(os.environ["SUPABASE_TEST_URL"], os.environ["SUPABASE_TEST_KEY"])


@pytest.fixture(autouse=True)
def cleanup():
    """Wipe all app tables before each test so runs are isolated."""
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE game_guess, guessed, made_by, guess, plays, "
            "answer, in_language, word, game, player, language CASCADE"
        )
    conn.close()
    yield


@pytest.fixture
def seeded_game(sb):
    """Creates alice (id=1, turn 1) vs bob (id=2, turn 2), answer=apple. Returns game_id."""
    sb.table("player").insert([
        {"player_id": 1, "username": "alice"},
        {"player_id": 2, "username": "bob"},
    ]).execute()

    game_id = sb.table("game").insert({"status": "in_progress"}).execute().data[0]["game_id"]

    sb.table("word").insert([{"word": "apple"}, {"word": "stone"}]).execute()
    sb.table("language").insert({"language_code": "en", "language_name": "English"}).execute()
    sb.table("in_language").insert([
        {"word": "apple", "language_code": "en"},
        {"word": "stone", "language_code": "en"},
    ]).execute()

    sb.table("answer").insert({"game_id": game_id, "word": "apple"}).execute()

    sb.table("plays").insert([
        {"player_id": 1, "game_id": game_id, "turn_order": 1},
        {"player_id": 2, "game_id": game_id, "turn_order": 2},
    ]).execute()

    return game_id
