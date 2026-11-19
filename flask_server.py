# CMSC 447 - Shared-State Wordle
# Created: 10/11/26


# Imports
from flask import Flask, request, jsonify
import helpers
import os
# IMPORT GAME CLASS
# IMPORT PLAYER/USER CLASS
# IMPORT GUESS CLASS
# IMPORT TEAM B's MODULE

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Request to create account
# TODO: @app.route("/users", methods=["POST"])

# Request to login
@app.route("/users/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    user = helpers.verify_user(username, password)

    if user is None:
        return jsonify({"error": "Invalid username or password"}), 401

    return jsonify(user), 200

# Request to get user's history
# TODO: @app.route("/users/<username>/history", methods=["POST"])

""" GAME MANAGEMENT ROUTES """

# Request to create a game
# TODO: @app.route("/games", methods=["POST"])
#def create_game():
#    game_id  = helpers.generate_game_id()
#    # Instantiate Game OBJ
#    return jsonify({"game_id": game_id}), 201

# Request to get game's state
# TODO: @app.route("/games/<game_id>", methods=["GET"])

# Request to join a game
# TODO: @app.route("/games/<game_id>/join", methods=["POST"])


""" GAMEPLAY ROUTES """

# Request to submit a guess
# TODO: @app.route("/games/<game_id>/guess", methods=["POST"])


if __name__ == "__main__":
    app.run(debug=True)

