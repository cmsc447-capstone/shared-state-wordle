# CMSC 447 - Shared-State Wordle
# Created: 10/11/26


# Imports
from flask import Flask, request, jsonify, session
import helpers
# IMPORT GAME CLASS
# IMPORT PLAYER/USER CLASS
# IMPORT GUESS CLASS
# IMPORT TEAM B's MODULE

app = Flask(__name__)

# Request to create account
@app.route("/users", methods=["POST"])


# Request to login
@app.route("/users/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    user = helpers.verify_user(username, password)

    if user is None:
        return jsonify({"message": "Invalid username or password"}), 401

    # Store user information in the session
    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return jsonify({
        "message": "Login successful",
        "username": user["username"]
    }), 200

# Request to get user's history
@app.route("/users/<username>/history", methods=["POST"])


""" GAME MANAGEMENT ROUTES """

# Request to create a game
@app.route("/games", methods=["POST"])
def create_game():
    game_id  = helpers.generate_game_id()
    # Instantiate Game OBJ
    return jsonify({"game_id": game_id}), 201

# Request to get game's state
@app.route("/games/<game_id>", methods=["GET"])

# Request to join a game
@app.route("/games/<game_id>/join", methods=["POST"])


""" GAMEPLAY ROUTES """

# Request to submit a guess
@app.route("/games/<game_id>/guess", methods=["POST"])


if __name__ == "__main__":
    app.run(debug=True)

