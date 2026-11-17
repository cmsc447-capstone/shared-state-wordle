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
# TODO: @app.route("/games/<uuid:game_id>", methods=["GET"])

""" MATCHMAKING ROUTES """

# Request to be matched against another player
# TODO: @app.route("/games/match", methods=["POST"])

# Request to leave matchmaking
# TODO: @app.route("/games/match", methods=["DELETE"])

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