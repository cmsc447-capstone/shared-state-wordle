# CMSC 447 - Shared-State Wordle
# Created: 10/11/26

# Imports
from flask import Flask, request, jsonify, g
import helpers
from werkzeug.exceptions import HTTPException
from auth import require_user
# IMPORT GAME CLASS
# IMPORT PLAYER/USER CLASS
# IMPORT GUESS CLASS
# IMPORT TEAM B's MODULE

app = Flask(__name__)
# This might change once we deploy
# with gunicorn but it also might not...
@app.errorhandler(HTTPException)
def handle_http_error(e):
    return jsonify({"error": e.name}), e.code

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
    except helpers.GameConflict as e:
        return jsonify({"error": str(e)}), 409

    return jsonify({"game_id": game["game_id"],
                    "status": game["status"],
                    "language": language,
                    }), 201

# Request to be matched against another player
# TODO: @app.route("/games", methods=["GET"])

# Request to get game's state
@app.route("/games/<uuid:game_id>", methods=["GET"]) # UUID:game_id Flask's built in UUID converter
@require_user()
def get_game_state(game_id):
    try:
        state = helpers.get_game_state(str(game_id), g.user.id)
    except helpers.GameNotFound:
        return jsonify({"error": "No game found with that game_id"}), 404
    except helpers.GameForbidden:
        return jsonify({"error": "You did not play in this game"}), 403
    return jsonify(state), 200

# Request to join a game
@app.route("/games/<uuid:game_id>/join", methods=["POST"]) # UUID:game_id Flask's built in UUID converter
@require_user()
def join_game(game_id):
    try:
        game = helpers.join_game(str(game_id), g.user.id)
    except helpers.GameNotFound:
        return jsonify({"error": "No game found with that game_id"}), 404
    except helpers.GameConflict as e:
        return jsonify({"error": str(e)}), 409

    return jsonify({"game_id": game["game_id"],
                    "status": game["status"],
                    "turn_order": 2,
                    }), 200

""" GAMEPLAY ROUTES """

# Request to submit a guess
# TODO: @app.route("/games/<game_id>/guess", methods=["POST"])

if __name__ == "__main__":
    app.run(debug=True)