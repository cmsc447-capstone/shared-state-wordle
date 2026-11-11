@app.route("/games/<game_id>", methods=["GET"])
def get_game_state(game_id):
    username = session.get("username")
    if not username:
        return jsonify({"error": "not logged in"}), 401

    try:
        game = helpers.get_game(game_id)
        players = helpers.get_game_players(game_id)
        guesses_raw = helpers.get_game_guesses(game_id)
    except Exception:
        return jsonify({"error": "unable to retrieve game state"}), 500

    if game is None:
        return jsonify({"error": "game not found"}), 404

    usernames = [p["username"] for p in players]
    if username not in usernames:
        return jsonify({"error": "you are not a player in this game"}), 403

    guesses = []
    for g in guesses_raw:
        guesses.append({
            "attempt_number": g["attempt_number"],
            "username": g["username"],
            "word": g["word"],
            "feedback": g["feedback"],
        })

    players_sorted = sorted(players, key=lambda p: p["turn_order"])
    current = players_sorted[len(guesses) % 2]

    return jsonify({
        "game_id": game["game_id"],
        "status": game["status"],
        "current_turn": current["username"],
        "current_turn_player": current["turn_order"],
        "guesses": guesses,
    }), 200
