# CMSC 447 - Shared-State Wordle
# Created: 10/11/26


# Imports
from flask import Flask, request, jsonify, session
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
        return jsonify({"message": "Invalid username or password"}), 401

    # Store user information in the session
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]

    return jsonify({
        "message": "Login successful",
        "username": user["username"]
    }), 200

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
@app.route("/games/<uuid:game_id>/guess", methods=["POST"])
@require_user()
def submit_guess(game_id):
    body = request.get_json(silent=True) or {}
    word = (body.get("guess") or "").strip().lower()
    if not word:
        return jsonify({"error": "guess is required"}), 400

    try:
        result = helpers.submit_guess(str(game_id), g.user.id, word)
    except helpers.GameNotFound:
        return jsonify({"error": "No game found with that game_id"}), 404
    except helpers.GameForbidden:
        return jsonify({"error": "You did not play in this game"}), 403
    except helpers.GameConflict as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(result), 201

if __name__ == "__main__":
    app.run(debug=True)

