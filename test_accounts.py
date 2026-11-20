from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from supabase import AuthApiError
from postgrest.exceptions import APIError
import app as app_module

URL = "/users"   # match your decorator
FAKE_ID = "11111111-2222-3333-4444-555555555555"
GOOD = {"username": "alice", "email": "alice@example.com", "password": "hunter2hunter2"}


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def fake_supabase(existing=None, create_error=None, insert_error=None):
    sb = MagicMock()

    # username check: table().select().ilike().limit().execute()
    sb.table.return_value.select.return_value.ilike.return_value \
        .limit.return_value.execute.return_value.data = existing or []

    # Auth user creation
    if create_error:
        sb.auth.admin.create_user.side_effect = create_error
    else:
        sb.auth.admin.create_user.return_value = SimpleNamespace(
            user=SimpleNamespace(id=FAKE_ID)
        )

    # player insert
    if insert_error:
        sb.table.return_value.insert.return_value.execute.side_effect = insert_error

    return sb


def use(monkeypatch, sb):
    monkeypatch.setattr(app_module, "admin", lambda: sb)


def test_success(client, monkeypatch):
    sb = fake_supabase()
    use(monkeypatch, sb)

    res = client.post(URL, json=GOOD)

    assert res.status_code == 201
    body = res.get_json()
    assert body["username"] == "alice"
    assert body["player_id"] == FAKE_ID
    assert "password" not in body

    # Auth got the credentials; the player row got the Auth id, and no password
    sb.auth.admin.create_user.assert_called_once()
    assert sb.auth.admin.create_user.call_args[0][0]["email"] == "alice@example.com"
    saved = sb.table.return_value.insert.call_args[0][0]
    assert saved["player_id"] == FAKE_ID
    assert saved["username"] == "alice"
    assert "password" not in saved


def test_duplicate_username(client, monkeypatch):
    sb = fake_supabase(existing=[{"player_id": "someone-else"}])
    use(monkeypatch, sb)

    res = client.post(URL, json=GOOD)

    assert res.status_code == 409
    sb.auth.admin.create_user.assert_not_called()


def test_duplicate_email(client, monkeypatch):
    err = AuthApiError("Email already registered", 422, "email_exists")
    sb = fake_supabase(create_error=err)
    use(monkeypatch, sb)

    res = client.post(URL, json=GOOD)

    assert res.status_code == 409
    sb.table.return_value.insert.assert_not_called()


def test_username_race_rolls_back_auth_user(client, monkeypatch):
    err = APIError({"message": "dup", "code": "23505", "hint": None, "details": None})
    sb = fake_supabase(insert_error=err)
    use(monkeypatch, sb)

    res = client.post(URL, json=GOOD)

    assert res.status_code == 409
    sb.auth.admin.delete_user.assert_called_once_with(FAKE_ID)


def test_insert_failure_rolls_back_auth_user(client, monkeypatch):
    sb = fake_supabase(insert_error=Exception("boom"))
    use(monkeypatch, sb)

    res = client.post(URL, json=GOOD)

    assert res.status_code == 500
    sb.auth.admin.delete_user.assert_called_once_with(FAKE_ID)


def test_auth_failure(client, monkeypatch):
    sb = fake_supabase(create_error=Exception("auth down"))
    use(monkeypatch, sb)

    res = client.post(URL, json=GOOD)

    assert res.status_code == 500
    sb.table.return_value.insert.assert_not_called()


def test_weak_password_from_supabase(client, monkeypatch):
    err = AuthApiError("Password too weak", 422, "weak_password")
    sb = fake_supabase(create_error=err)
    use(monkeypatch, sb)

    assert client.post(URL, json=GOOD).status_code == 400


@pytest.mark.parametrize("body", [
    {},
    {**GOOD, "username": "ab"},              # too short
    {**GOOD, "username": "bad name!"},       # invalid characters
    {**GOOD, "email": "not-an-email"},       # bad email
    {**GOOD, "password": "short"},           # short password
])
def test_bad_input(client, monkeypatch, body):
    sb = fake_supabase()
    use(monkeypatch, sb)

    assert client.post(URL, json=body).status_code == 400
    sb.auth.admin.create_user.assert_not_called()