import pytest
import helpers


# ---------------------------------------------------------------------------
# submit_guess: core gameplay
# ---------------------------------------------------------------------------

def test_win(sb, seeded_game):
    """Guessing the answer should return all-green feedback and flip to won."""
    result = helpers.submit_guess(seeded_game, 1, "apple")
    assert result["feedback"] == ["G", "G", "G", "G", "G"]
    assert result["status"] == "won"

    # persisted correctly
    saved = sb.table("guessed").select("*").execute().data
    assert len(saved) == 1 and saved[0]["word"] == "apple"


def test_wrong_guess(sb, seeded_game):
    """A wrong but valid word should keep the game in progress."""
    result = helpers.submit_guess(seeded_game, 1, "stone")
    assert result["status"] == "in_progress"
    assert len(result["feedback"]) == 5
    assert result["feedback"] != ["G", "G", "G", "G", "G"]


def test_out_of_turn(sb, seeded_game):
    """bob (turn 2) guessing first should be rejected."""
    with pytest.raises(helpers.GameConflict, match="not your turn"):
        helpers.submit_guess(seeded_game, 2, "apple")


def test_invalid_word(sb, seeded_game):
    """A word not in the dictionary should raise ValueError."""
    with pytest.raises(ValueError):
        helpers.submit_guess(seeded_game, 1, "zzzzz")


def test_unknown_game(sb):
    """A game_id that doesn't exist should raise GameNotFound."""
    with pytest.raises(helpers.GameNotFound):
        helpers.submit_guess("00000000-0000-0000-0000-000000000000", 1, "apple")


def test_cannot_guess_on_finished_game(sb, seeded_game):
    """Once the game is won/lost, no more guesses."""
    sb.table("game").update({"status": "won"}).eq("game_id", seeded_game).execute()
    with pytest.raises(helpers.GameConflict, match="already ended"):
        helpers.submit_guess(seeded_game, 1, "stone")


def test_turn_alternates(sb, seeded_game):
    """After alice guesses, the next turn should belong to bob."""
    result = helpers.submit_guess(seeded_game, 1, "stone")
    assert result["status"] == "in_progress"

    # now bob can guess
    result2 = helpers.submit_guess(seeded_game, 2, "apple")
    assert result2["status"] == "won"


# ---------------------------------------------------------------------------
# find_active_game
# ---------------------------------------------------------------------------

def test_find_active_game_for_each_player(sb, seeded_game):
    """Both players in the game should find it."""
    assert helpers.find_active_game(1) == seeded_game
    assert helpers.find_active_game(2) == seeded_game


def test_find_active_game_none(sb):
    """A user not in any game should get GameNotFound."""
    with pytest.raises(helpers.GameNotFound):
        helpers.find_active_game(999)


def test_find_active_game_ignores_finished(sb, seeded_game):
    """A won/lost game should not be returned as active."""
    sb.table("game").update({"status": "won"}).eq("game_id", seeded_game).execute()
    with pytest.raises(helpers.GameNotFound):
        helpers.find_active_game(1)
