def evaluate_guess(guess: str, target: str) -> dict:
    # TEMPORARY STUB for Team B. Replace the body with their function.
    # Assumed return shape (confirm with Team B):
    #   {"valid": True,  "feedback": "GBYBB"}
    #   {"valid": False, "message": "Not a valid word"}
    if len(guess) != 5 or not guess.isalpha():
        return {"valid": False, "message": "Guess must be a 5-letter word"}
    feedback = "".join("G" if g == t else "B" for g, t in zip(guess, target))
    return {"valid": True, "feedback": feedback}


def find_active_game(user_id: str) -> dict | None:
    plays = supabase.table("plays").select("game_id").eq("user_id", user_id).execute().data
    ids = [p["game_id"] for p in plays]
    if not ids:
        return None
    games = (
        supabase.table("game").select("*")
        .in_("game_id", ids).eq("status", "started")
        .order("created_at", desc=True).limit(1).execute().data
    )
    return games[0] if games else None


def get_target_word(game_id: str) -> str | None:
    rows = supabase.table("answer").select("word").eq("game_id", game_id).execute().data
    return rows[0]["word"] if rows else None


def insert_guess(game_id: str, user_id: str, word: str, feedback: str) -> dict:
    prior = supabase.table("guess").select("attempt_num").eq("game_id", game_id).execute().data
    attempt_num = len(prior) + 1
    return supabase.table("guess").insert({
        "game_id": game_id,
        "attempt_num": attempt_num,
        "user_id": user_id,
        "word": word,
        "feedback": feedback,
    }).execute().data[0]
