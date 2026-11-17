# ============================================================
# submit_guess helpers
# ============================================================

import os
from supabase import create_client
import team_b

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

    Rules:
      - Each player gets up to 6 guesses; they stop on a correct guess.
      - Game ends when BOTH players have finished.
      - Outcome: fewer attempts wins; equal = draw; both exhausted = draw.

    Returns:
        {game_id, guess, feedback, attempt_number, status, winner, current_turn}

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

    feedback = team_b.compute_feedback(word, answer_word)

    all_guesses = c.table("guess").select("attempt_number").execute().data
    attempt_number = max([g["attempt_number"] for g in all_guesses], default=0) + 1

    c.table("guess").insert({"attempt_number": attempt_number, "feedback": feedback}).execute()
    c.table("made_by").insert({"attempt_number": attempt_number, "player_id": user_id}).execute()
    c.table("guessed").insert({"attempt_number": attempt_number, "word": word}).execute()
    c.table("game_guess").insert({"game_id": game_id, "attempt_number": attempt_number}).execute()

    # --- tally every player in this game ---
    game_attempt_ids = {g["attempt_number"] for g in game_guesses} | {attempt_number}
    per_player = {}
    for p in players:
        made = c.table("made_by").select("attempt_number").eq("player_id", p["player_id"]).execute().data
        ids = sorted(m["attempt_number"] for m in made if m["attempt_number"] in game_attempt_ids)
        finished = False
        won_on_nth = None
        for idx, an in enumerate(ids, start=1):
            row = c.table("guess").select("feedback").eq("attempt_number", an).execute().data
            if row and all(f == "G" for f in row[0]["feedback"]):
                finished = True
                won_on_nth = idx
                break
        if not finished and len(ids) >= 6:
            finished = True
        per_player[p["player_id"]] = {"finished": finished, "won_on_nth": won_on_nth}

    everyone_finished = all(r["finished"] for r in per_player.values())

    if everyone_finished:
        a, b = list(per_player.keys())
        a_win = per_player[a]["won_on_nth"]
        b_win = per_player[b]["won_on_nth"]

        if a_win is not None and b_win is not None:
            if a_win < b_win:
                outcome = {a: "won", b: "lost"}
            elif b_win < a_win:
                outcome = {a: "lost", b: "won"}
            else:
                outcome = {a: "draw", b: "draw"}
        elif a_win is not None:
            outcome = {a: "won", b: "lost"}
        elif b_win is not None:
            outcome = {a: "lost", b: "won"}
        else:
            outcome = {a: "draw", b: "draw"}

        winner_id = next((pid for pid, res in outcome.items() if res == "won"), None)
        new_status = "won" if winner_id is not None else "draw"

        c.table("game").update({"status": new_status}).eq("game_id", game_id).execute()
        for pid, res in outcome.items():
            c.table("plays").update({"result": res}) \
                .eq("game_id", game_id).eq("player_id", pid).execute()
    else:
        winner_id = None
        new_status = "in_progress"

    # winner's username so the client can display "alice won"
    winner_username = None
    if winner_id is not None:
        row = c.table("player").select("username").eq("player_id", winner_id).execute().data
        if row:
            winner_username = row[0]["username"]

    # next player's id, or None if game is over
    if everyone_finished:
        current_turn = None
    else:
        next_player = players[(len(game_guesses) + 1) % len(players)]
        current_turn = next_player["player_id"]

    return {
        "game_id": game_id,
        "guess": word,
        "feedback": feedback,
        "attempt_number": attempt_number,
        "status": new_status,
        "winner": winner_username,
        "current_turn": current_turn,
    }
