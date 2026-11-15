# ============================================================
# submit_guess helpers
# ============================================================

import os
from supabase import create_client

# only keep these if your helpers.py doesn't already define them
class GameNotFound(Exception): pass
class GameForbidden(Exception): pass
class GameConflict(Exception): pass


def _client():
    url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_TEST_URL", "http://127.0.0.1:54321")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_TEST_KEY")
    return create_client(url, key)


def find_active_game(user_id):
    """Find the user's in-progress game and return its game_id.

    Raises:
        GameNotFound - user isn't playing in any active game
    """
    c = _client()
    plays = c.table("plays").select("game_id").eq("player_id", user_id).execute().data
    if not plays:
        raise GameNotFound()

    game_ids = [p["game_id"] for p in plays]
    games = (
        c.table("game")
        .select("*")
        .in_("game_id", game_ids)
        .eq("status", "in_progress")
        .order("created_at", desc=True)
        .execute()
        .data
    )
    if not games:
        raise GameNotFound()
    return games[0]["game_id"]


def submit_guess(game_id, user_id, word):
    """Validate + record a guess, update game state if it ended.

    Returns:
        {game_id, guess, feedback, attempt_number, status}

    Raises:
        GameNotFound  - no game with that id
        GameForbidden - user isn't in the game
        GameConflict  - game ended / not this user's turn / no answer set
        ValueError    - word not in the dictionary
    """
    c = _client()

    game = c.table("game").select("*").eq("game_id", game_id).execute().data
    if not game:
        raise GameNotFound()
    if game[0]["status"] != "in_progress":
        raise GameConflict("game already ended")

    players = (
        c.table("plays").select("*").eq("game_id", game_id)
        .order("turn_order").execute().data
    )
    if user_id not in [p["player_id"] for p in players]:
        raise GameForbidden()

    game_guesses = c.table("game_guess").select("*").eq("game_id", game_id).execute().data
    current = players[len(game_guesses) % len(players)]
    if current["player_id"] != user_id:
        raise GameConflict("not your turn")

    answer = c.table("answer").select("*").eq("game_id", game_id).execute().data
    if not answer:
        raise GameConflict("no answer set")
    answer_word = answer[0]["word"]

    if not c.table("word").select("word").eq("word", word).execute().data:
        raise ValueError(f"'{word}' not in dictionary")

    import team_b
    feedback = team_b.compute_feedback(word, answer_word)

    all_guesses = c.table("guess").select("attempt_number").execute().data
    attempt_number = max([g["attempt_number"] for g in all_guesses], default=0) + 1

    c.table("guess").insert({"attempt_number": attempt_number, "feedback": feedback}).execute()
    c.table("made_by").insert({"attempt_number": attempt_number, "player_id": user_id}).execute()
    c.table("guessed").insert({"attempt_number": attempt_number, "word": word}).execute()
    c.table("game_guess").insert({"game_id": game_id, "attempt_number": attempt_number}).execute()

    won = all(f == "G" for f in feedback)
    if won:
        c.table("game").update({"status": "won"}).eq("game_id", game_id).execute()
        c.table("plays").update({"result": "won"}).eq("game_id", game_id).eq("player_id", user_id).execute()

    return {
        "game_id": game_id,
        "guess": word,
        "feedback": feedback,
        "attempt_number": attempt_number,
        "status": "won" if won else "in_progress",
    }
