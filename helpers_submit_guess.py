import os
from supabase import create_client
import team_b

class GameNotFound(Exception): pass
class GameForbidden(Exception): pass
class GameConflict(Exception): pass


def _client():
    url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_TEST_URL", "http://127.0.0.1:54321")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_TEST_KEY")
    return create_client(url, key)


def find_active_game(user_id):
    """Find the user's in-progress game and return its game_id."""
    c = _client()
    plays = c.table("plays").select("game_id").eq("player_id", user_id).execute().data
    if not plays:
        raise GameNotFound()
    game_ids = [p["game_id"] for p in plays]
    games = (
        c.table("game").select("*").in_("game_id", game_ids)
        .eq("status", "in_progress").order("created_at", desc=True).execute().data
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
    game_attempt_ids = {g["attempt_number"] for g in game_guesses}

    # per-player state
    guesses_by_player = {}
    won_on_nth = {}
    finished_ids = set()
    for p in players:
        pid = p["player_id"]
        made = c.table("made_by").select("attempt_number").eq("player_id", pid).execute().data
        ids = sorted(m["attempt_number"] for m in made if m["attempt_number"] in game_attempt_ids)
        guesses_by_player[pid] = ids
        won_nth = None
        for idx, an in enumerate(ids, start=1):
            row = c.table("guess").select("feedback").eq("attempt_number", an).execute().data
            if row and all(f == "G" for f in row[0]["feedback"]):
                won_nth = idx
                break
        won_on_nth[pid] = won_nth
        if won_nth is not None or len(ids) >= 6:
            finished_ids.add(pid)

    def next_unfinished():
        n = sum(len(v) for v in guesses_by_player.values())
        for offset in range(len(players) * 2):
            candidate = players[(n + offset) % len(players)]
            if candidate["player_id"] not in finished_ids:
                return candidate
        return None

    current = next_unfinished()
    if current is None:
        raise GameConflict("game already ended")
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

    # update this player's tally
    guesses_by_player[user_id].append(attempt_number)
    if all(f == "G" for f in feedback):
        won_on_nth[user_id] = len(guesses_by_player[user_id])
        finished_ids.add(user_id)
    elif len(guesses_by_player[user_id]) >= 6:
        finished_ids.add(user_id)

    # is the game over?
    if len(finished_ids) == len(players):
        a, b = players[0]["player_id"], players[1]["player_id"]
        a_win, b_win = won_on_nth[a], won_on_nth[b]
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

        winner_id = next((pid for pid, r in outcome.items() if r == "won"), None)
        new_status = "won" if winner_id is not None else "draw"
        c.table("game").update({"status": new_status}).eq("game_id", game_id).execute()
        for pid, r in outcome.items():
            c.table("plays").update({"result": r}).eq("game_id", game_id).eq("player_id", pid).execute()
        current_turn = None
    else:
        winner_id = None
        new_status = "in_progress"
        nxt = next_unfinished()
        current_turn = nxt["player_id"] if nxt else None

    winner_username = None
    if winner_id is not None:
        row = c.table("player").select("username").eq("player_id", winner_id).execute().data
        if row:
            winner_username = row[0]["username"]

    return {
        "game_id": game_id,
        "guess": word,
        "feedback": feedback,
        "attempt_number": attempt_number,
        "status": new_status,
        "winner": winner_username,
        "current_turn": current_turn,
    }
