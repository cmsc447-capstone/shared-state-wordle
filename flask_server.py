# CMSC 447 - Shared-State Wordle
# Created: 11/2/26


# Imports
import os
from collections import defaultdict
from flask import Flask, jsonify
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


@app.route("/users/<username>/history", methods=["GET"])
def user_history(username):
    try:
        # 1. Find the player
        player_res = (
            supabase.table("player")
            .select("player_id, username, created_at, preferred_language_code")
            .eq("username", username)
            .maybe_single()
            .execute()
        )
        if player_res is None or player_res.data is None:
            return jsonify({"message": "User not found"}), 404
        player = player_res.data

        # 2. Games this player took part in (plays -> game via FK)
        plays_res = (
            supabase.table("plays")
            .select("turn_order, result, game(game_id, status, created_at, ended_at)")
            .eq("player_id", player["player_id"])
            .execute()
        )

        # 3. This player's guesses
        guesses_res = (
            supabase.table("guess")
            .select("game_id, attempt_number, guessed_word, feedback, created_at")
            .eq("player_id", player["player_id"])
            .order("attempt_number")
            .execute()
        )

        # Group guesses by game
        guesses_by_game = defaultdict(list)
        for g in guesses_res.data:
            guesses_by_game[g["game_id"]].append(g)

        history = []
        for row in plays_res.data:
            game = row["game"]
            history.append({
                **game,
                "turn_order": row["turn_order"],
                "result": row["result"],
                "guesses": guesses_by_game.get(game["game_id"], []),
            })
        history.sort(key=lambda g: g["created_at"], reverse=True)

        return jsonify({
            "username": player["username"],
            "preferred_language": player["preferred_language_code"],
            "history": history,
        }), 200

    except Exception as e:
        return jsonify({"message": "Database error", "error": str(e)}), 500