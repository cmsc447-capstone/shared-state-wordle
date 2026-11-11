# CMSC 447 - Shared-State Wordle
# Created: 10/11/26


# Imports
from flask import Flask, request, jsonify, g
import helpers
from auth import require_user
# IMPORT GAME CLASS
# IMPORT PLAYER/USER CLASS
# IMPORT GUESS CLASS
# IMPORT TEAM B's MODULE

app = Flask(__name__)

"""

EXAMPLE ENDPOINT

@app.route("/hello", methods=["GET"])
def hello():
    return jsonify({"message": "Hello!"})

"""

""" USER ROUTES """

# Request to create account
# TODO: @app.route("/users", methods=["POST"])

# Request to login
# TODO: @app.route("/users/login", methods=["POST"])

# Request to get user's history
# TODO: @app.route("/users/<username>/history", methods=["POST"])

""" GAME MANAGEMENT ROUTES """

# Request to create a game
@app.route("/games", methods=["POST"])
@require_user()
def create_game():
    body = request.get_json(silent=True) or {}
    language = body.get("language") or helpers.get_player_language(g.user.id)

    try:
        game = helpers.create_game(g.user.id, language)
    except ValueError as e: # when there is no language or no words for a language
        return jsonify({"error": str(e)}), 400

    return jsonify({"game_id": game["game_id"], "status": game["status"], "language": language}), 201


# Request to get game's state
# TODO: @app.route("/games/<game_id>", methods=["GET"])

# Request to join a game
@app.route("/games/<uuid:game_id>/join", methods=["POST"]) # UUID:game_id Flask's built in UUID converter
@require_user()
def join_game(game_id):
    try:
        game = helpers.join_game(str(game_id), g.user.id)
    except helpers.GameNotFound:
        return jsonify({"error": "game not found"}), 404
    except helpers.GameConflict as e:
        return jsonify({"error": str(e)}), 409

    return jsonify({"game_id": game["game_id"], "status": game["status"], "turn_order": 2}), 200

""" GAMEPLAY ROUTES """

# Request to submit a guess
# TODO: @app.route("/games/<game_id>/guess", methods=["POST"])

if __name__ == "__main__":
    app.run(debug=True)