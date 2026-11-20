# CMSC 447 - Shared-State Wordle
# Created: 10/11/26

import re
from flask import request, jsonify
from supabase import AuthApiError          # error raised by Supabase Auth calls
from postgrest.exceptions import APIError  # error raised by table queries
from db import admin

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def _escape_like(text: str) -> str:
    # In ilike, "_" and "%" are wildcards. Escape them so "a_b" doesn't match "axb".
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.route("/users", methods=["POST"])
def create_account():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    language = data.get("preferred_language_code", "en")

    # --- Validate input ---
    if not USERNAME_RE.match(username):
        return jsonify({
            "message": "Username must be 3-20 characters: letters, numbers, underscores"
        }), 400
    if not EMAIL_RE.match(email):
        return jsonify({"message": "A valid email is required"}), 400
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "message": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        }), 400

    supabase = admin()

    # --- Is the username taken? ---
    try:
        existing = (
            supabase.table("player")
            .select("player_id")
            .ilike("username", _escape_like(username))
            .limit(1)
            .execute()
        )
    except Exception:
        return jsonify({"message": "Database error"}), 500

    if existing.data:
        return jsonify({"message": "Username already taken"}), 409

    # --- Step 1: create the Auth user (Supabase hashes the password) ---
    try:
        auth_result = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,   # skip the confirmation email
        })
    except AuthApiError as e:
        if e.code == "email_exists":
            return jsonify({"message": "Email already registered"}), 409
        if e.code == "weak_password":
            return jsonify({"message": "Password is too weak"}), 400
        return jsonify({"message": "Account creation failed"}), 500
    except Exception:
        return jsonify({"message": "Account creation failed"}), 500

    user_id = str(auth_result.user.id)

    # --- Step 2: save the player row, using the Auth id as player_id ---
    try:
        supabase.table("player").insert({
            "player_id": user_id,
            "username": username,
            "preferred_language_code": language,
        }).execute()
    except Exception as e:
        # The Auth user now has no player row, so remove it to avoid orphans
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception:
            pass

        code = getattr(e, "code", None)
        if code == "23505":    # unique_violation: someone grabbed the username first
            return jsonify({"message": "Username already taken"}), 409
        if code == "23503":    # foreign_key_violation: bad language code
            return jsonify({"message": "Unknown language code"}), 400
        return jsonify({"message": "Account creation failed"}), 500

    return jsonify({
        "message": "Account created",
        "player_id": user_id,
        "username": username,
    }), 201