# CMSC 447 - Shared-State Wordle

# Shared test fixtures. Test will run against your local Supabase stack
# Please ensure that you have ran:
# >$ supabase start
# and are using the rights keys in .env

import os
import uuid
import pytest
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

from flask_server import app as flask_app   # noqa: E402
from db import admin, rows                  # noqa: E402

PASSWORD = "password123"

# This tests creates a new player with a random username and
# returns their id, username, token, and request headers
def _sign_up_test_player() -> dict:
    client = create_client(os.environ["SUPABASE_URL"],
                           os.environ["SUPABASE_PUBLISHABLE_KEY"])
    username = f"test_{uuid.uuid4().hex[:10]}"
    res = client.auth.sign_up({
        "email": f"{username}@test.local",
        "password": PASSWORD,
        "options": {"data": {"username": username}},
    })
    assert res.user is not None
    assert res.session is not None # Only works with enable_confirmations = false [config.toml]

    token = res.session.access_token
    return {
        "id": res.user.id,
        "username": username,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }