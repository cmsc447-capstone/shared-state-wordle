import pytest
import helpers


def test_win_and_report_winner(sb, seeded_game):
    """alice wins on 2nd try, bob exhausts 6 → alice wins, named in response."""
    helpers.submit_guess(seeded_game, 1, "stone")
    helpers.submit_guess(seeded_game, 2, "stone")
    r1 = helpers.submit_guess(seeded_game, 1, "apple")   # alice 2nd — in progress
    assert r1["status"] == "in_progress"
    assert r1["winner"] is None

    # bob already has 1 guess; give him 4 more, then a 6th to end
    for _ in range(4):
        helpers.submit_guess(seeded_game, 2, "stone")
    r2 = helpers.submit_guess(seeded_game, 2, "stone")   # bob's 6th
    assert r2["status"] == "won"
    assert r2["winner"] == "alice"
    assert r2["current_turn"] is None


def test_draw_same_attempts(sb, seeded_game):
    """Both win on their 3rd try → draw."""
    helpers.submit_guess(seeded_game, 1, "stone")
    helpers.submit_guess(seeded_game, 2, "stone")
    helpers.submit_guess(seeded_game, 1, "stone")
    helpers.submit_guess(seeded_game, 2, "stone")
    helpers.submit_guess(seeded_game, 1, "apple")        # alice wins 3rd
    r = helpers.submit_guess(seeded_game, 2, "apple")    # bob wins 3rd
    assert r["status"] == "draw"
    assert r["winner"] is None


def test_draw_both_exhaust(sb, seeded_game):
    """12 wrong guesses → draw."""
    for i in range(12):
        player = (i % 2) + 1
        r = helpers.submit_guess(seeded_game, player, "stone")
    assert r["status"] == "draw"
    assert r["winner"] is None


def test_fewer_attempts_wins(sb, seeded_game):
    """alice wins on 2nd, bob wins on 4th → alice wins."""
    helpers.submit_guess(seeded_game, 1, "stone")
    helpers.submit_guess(seeded_game, 2, "stone")
    helpers.submit_guess(seeded_game, 1, "apple")        # alice 2nd
    helpers.submit_guess(seeded_game, 2, "stone")        # bob 3rd
    r = helpers.submit_guess(seeded_game, 2, "apple")    # bob 4th
    assert r["status"] == "won"
    assert r["winner"] == "alice"


def test_wrong_guess_keeps_playing(sb, seeded_game):
    result = helpers.submit_guess(seeded_game, 1, "stone")
    assert result["status"] == "in_progress"
    assert result["winner"] is None
    assert result["current_turn"] == 2


def test_out_of_turn(sb, seeded_game):
    with pytest.raises(helpers.GameConflict, match="not your turn"):
        helpers.submit_guess(seeded_game, 2, "apple")


def test_invalid_word(sb, seeded_game):
    with pytest.raises(ValueError):
        helpers.submit_guess(seeded_game, 1, "zzzzz")


def test_unknown_game(sb):
    with pytest.raises(helpers.GameNotFound):
        helpers.submit_guess("00000000-0000-0000-0000-000000000000", 1, "apple")


def test_cannot_guess_on_finished_game(sb, seeded_game):
    sb.table("game").update({"status": "won"}).eq("game_id", seeded_game).execute()
    with pytest.raises(helpers.GameConflict, match="already ended"):
        helpers.submit_guess(seeded_game, 1, "stone")


def test_find_active_game_for_each_player(sb, seeded_game):
    assert helpers.find_active_game(1) == seeded_game
    assert helpers.find_active_game(2) == seeded_game


def test_find_active_game_none(sb):
    with pytest.raises(helpers.GameNotFound):
        helpers.find_active_game(999)


def test_find_active_game_ignores_finished(sb, seeded_game):
    sb.table("game").update({"status": "won"}).eq("game_id", seeded_game).execute()
    with pytest.raises(helpers.GameNotFound):
        helpers.find_active_game(1)
