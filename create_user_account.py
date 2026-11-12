from flask import Flask, request, jsonify
from supabase_client import auth_client  # adjust module name

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    try:
        res = auth_client().auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"username": username}},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"id": res.user.id, "username": username}), 201