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

""" USER ROUTES """

# Request to create account
# TODO: @app.route("/users", methods=["POST"])

# Request to login
# TODO: @app.route("/users/login", methods=["POST"])

# Request to get user's history
# TODO: @app.route("/users/<username>/history", methods=["POST"])

""" GAME MANAGEMENT ROUTES """

# Request to get a game's state
@app.route("/games/<uuid:game_id>", methods=["GET"])
@require_user()
def get_game_state(game_id):
    try:
        state = helpers.get_game_state(str(game_id), g.user.id)
    except helpers.GameNotFound:
        return jsonify({"error": "No game found with that game_id"}), 404
    except helpers.GameForbidden:
        return jsonify({"error": "You did not play in this game"}), 403
    return jsonify(state), 200

""" MATCHMAKING ROUTES """

# Request to be matched against another player
@app.route("/games/match", methods=["POST"])
@require_user()
def join_matchmaking():
    try:
        game = helpers.match_player(g.user.id)
    except helpers.GameConflict as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e: # no words in lang
        return jsonify({"error": str(e)}), 400

    if game is None:
        return jsonify({"queued": True, "game_id": None}), 202
    return jsonify({"queued": False, "game_id": game["game_id"]}), 201

# Request to leave matchmaking
@app.route("/games/match", methods=["DELETE"])
@require_user()
def leave_matchmaking():
    helpers.leave_queue(g.user.id)
    return "", 204 # Always returns the same result where or not player was queued

""" INVITE ROUTES """

# Request to create an invite game
# TODO: app.route("/games", methods=["POST"])

# Request to cancel an invite game
# TODO: app.route("/games", methods=["DELETE"])

# Request to join an invite game
# TODO: app.route("/games/<uuid:game_id/join", methods=["POST"])

""" GAMEPLAY ROUTES """

# Request to submit a guess
# TODO: @app.route("/games/<game_id>/guess", methods=["POST"])

if __name__ == "__main__":
    app.run(debug=True)