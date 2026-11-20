# CMSC 447 - Shared-State Wordle
# Created: 10/11/26

from db import admin, auth_client 
supabase = admin()

def verify_user(username: str, password: str) -> dict[str, str] | None:
    # Find the user's email using their username
    response = (
        supabase
        .table("player")
        .select("player_id, username")
        .eq("username", username)
        .maybe_single()
        .execute()
    )
    
    if response is None or not isinstance(response.data, dict):
        return None

    row = response.data
    player_id = str(row["player_id"])
    db_username = str(row["username"])

    # Retrieve the user's email from Supabase Auth
    auth_user = admin().auth.admin.get_user_by_id(player_id)
    email = auth_user.user.email
    if not email:
        return None

    # Authenticate with Supabase Auth
    try:
        auth_response = auth_client().auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
    except Exception:
        return None

    if auth_response.user is None:
        return None

    return {
        "user_id": auth_response.user.id,
        "username": db_username,
        "access_token": auth_response.session.access_token,
        "refresh_token": auth_response.session.refresh_token,
        "expires_at": auth_response.session.expires_at
    }