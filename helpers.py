# CMSC 447 - Shared-State Wordle
# Created: 10/11/26

from db import admin, auth_client 
supabase = admin()

def verify_user(username, password):
    # Find the user's email using their username
    response = (
        supabase
        .table("player")
        .select("player_id, username")
        .eq("username", username)
        .maybe_single()
        .execute()
    )
    
    if response is None:
        return None

    player_id = response.data["player_id"]

    # Retrieve the user's email from Supabase Auth
    auth_user = admin().auth.admin.get_user_by_id(player_id)
    email = auth_user.user.email

    # Authenticate with Supabase Auth
    try:
        auth_response = auth_client().auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # Return the authenticated user's information
        return {
            "user_id": auth_response.user.id,
            "username": response.data["username"]
        }

    except Exception:
        return None