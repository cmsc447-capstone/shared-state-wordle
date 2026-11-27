
import requests

BASE_URL = "http://127.0.0.1:5000"


# Test successfully changing a player's language
def test_change_language(sofia, db):
    response = (
        db.table("language")
        .select("language_code")
        .limit(1)
        .execute()
    )

    lang_code = response.data[0]["language_code"]

    response = requests.post(
        f"{BASE_URL}/users/edit/language",
        json={"lang_code": lang_code},
        headers=sofia["headers"]
    )

    assert response.status_code == 200
    assert response.json()["lang_code"] == lang_code

    # Verify database update
    player = (
        db.table("player")
        .select("language")
        .eq("player_id", sofia["player_id"])
        .execute()
    )

    assert player.data[0]["language"] == lang_code


# Test invalid language code
def test_invalid_language(sofia):
    response = requests.post(
        f"{BASE_URL}/users/edit/language",
        json={"lang_code": "invalid"},
        headers=sofia["headers"]
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Invalid language code"


# Test missing language code
def test_missing_language(sofia):
    response = requests.post(
        f"{BASE_URL}/users/edit/language",
        json={},
        headers=sofia["headers"]
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Missing language code"
