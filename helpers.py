# CMSC 447 - Shared-State Wordle
import random
from postgrest.types import CountMethod
from postgrest.exceptions import APIError
from db import admin, rows

OPEN_STATUS = ["waiting", "started"] # anything but finished

""" ERRORS """

class GameNotFound(Exception):
    """No game with that ID"""

class GameConflict(Exception):
    """Your request could not be completed"""

class GameForbidden(Exception):
    """Caller isn't a player in requested game."""

class PlayerNotFound(Exception):
    """No player found with for that ID"""

""" WORD HELPERS """

def pick_answer_word(language: str) -> str:
    """ Returns a randomly selected for from the word table for language """

    # Total number of words in a language
    count_res = (admin().table("word").select("word", count=CountMethod.exact).eq("language", language).limit(1).execute())
    total = count_res.count or 0
    if total == 0:
        raise ValueError(f"There are no words available in '{language}'")

    # Fetch a word at a random position using bounds from total
    offset = random.randrange(total)
    res = (admin().table("word")
           .select("word")
           .eq("language", language)
           .order("word")
           .range(offset, offset)
           .execute())
    data = rows(res)
    if not data:
        raise ValueError(f"There are no words available in '{language}'")
    return data[0]["word"]

""" PLAYER HELPERS """

def get_player_language(player_id: str) -> str | None:
    """ Returns a players preferred language and none if no player is found """

    res = (admin()
           .table("player")
           .select("language")
           .eq("player_id", player_id)
           .execute())
    data = rows(res)
    return data[0]["language"] if data else None

def get_open_game(player_id: str) -> dict | None:
    """ Returns that game_id and status if a player is in an unfinished game and
        return None if player has no unfinished games (games_status in OPEN_STATUS)"""

    res = (admin().table("plays")                   # SELECT g.game_id, g.status
           .select("game!inner(game_id, status)")   # FROM plays AS p JOIN game AS g ON g.game_id = p.game_id
           .eq("player_id", player_id)              # WHERE p.player_id = player_id
           .in_("game.status", OPEN_STATUS)         #   AND g.status IN ('waiting', 'started')
           .limit(1)                                # LIMIT 1
           .execute())
    data = rows(res)
    return data[0]["game"] if data else None

def release_player (player_id: str, join: str | None = None) -> None:
    """ Frees the player to start a different action. This function drops whatever
        the player was waiting, so that they can join a different game """

    game = get_open_game(player_id)                             # 1. Find the players unfinished games. If the player
    if game is not None:                                        #    has no unfinished games. Then game = None 
        if game["game_id"] == join:                             # 2. If the game they want to leave is same game they
            raise GameConflict("You are already in this game")  #    want to join refuse the request
        if game["status"] != "waiting":                         # 3. If the game they want to leave has a status of
            raise GameConflict("You are already in a game")     #    'started' refuse the request
        try:                                                    # 4. If the game they want to leave hasn't started
            cancel_game(game["game_id"], player_id)             #    and isn't the same game they want to join
        except GameNotFound:                                    #    then cancel the game
            pass
    leave_queue(player_id)

""" MATCHMAKING QUEUE HELPERS """

def in_queue(player_id: str) -> bool:
    """ Returns true is the player is currently listed in the queue """

    res = (admin().table("matchmaking_queue")   # SELECT player_id
           .select("player_id")                 # FROM matchmaking_queue
           .eq("player_id", player_id)          # WHERE player_id = player_id
           .execute())
    return len(rows(res)) > 0

def join_queue(player_id: str, language: str) -> None:
    """ Insert the player and their language into the matchmaking queue """

    try:
        (admin().table("matchmaking_queue")     # INSERT INTO matchmaking_queue
         .insert({"player_id": player_id, "language": language})           # (player_id, language)
         .execute())
    except APIError as e:
        if e.code != "23505": # unique_violation: Insertion failed because player is already in queue
            raise

def leave_queue(player_id: str) -> None:
    """ Removes the player from the matchmaking queue. Their row is deleted from 
        matchmaking_queue table. If no player_id is found in this table nothing
        happens. This function is safe to call even if player_id is not it table """

    (admin().table("matchmaking_queue")     
     .delete()                              # DELETE FROM matchmaking_queue
     .eq("player_id", player_id)            # WHERE player_id = player_id
     .execute())

def find_opponent(player_id: str, language: str) -> dict | None:
    """ Finds and assigns an opponet, decided by who has been waiting the the queue 
        the longest """

    db = admin()
    waitlist = rows(db.table("matchmaking_queue")   # SELECT player_id
                    .select("player_id")            # FROM matchmaking_queue
                    .eq("language", language)       # WHERE language = language
                    .neq("player_id", player_id)    #   AND player_id != player_id
                    .order("joined_at")             # ORDER BY joined_at
                    .limit(5)                       # LIMIT 5
                    .execute())
    # Removing the to-be-opponent from the waitlist
    for w in waitlist:
        opponent = rows(db.table("matchmaking_queue")       # DELETE
                        .delete()                           # FROM matchmaking_queue
                        .eq("player_id", w["player_id"])    # WHERE player_id = w.player_id
                        .execute())                         # RETURNING *
        if opponent:
            return opponent[0]
    return None

def match_player(player_id: str) -> dict | None:
    """ Pairs player with the player with with longest waiting time in their language
        if no player is avaible to be matched with the player is placed into the
        queue. If a match is found the started games row is reutrned, otherwise none """

    language = get_player_language(player_id) # returns none if no result if found for player_id
    if language is None:
        raise PlayerNotFound(player_id)
    
    if in_queue(player_id):     # If this player is already in the queue? Return none the player
        return None             # keeps waiting, and their time of remains the same. Otherwise, 
    release_player(player_id)   # release the player first so they can join the queue.

    opponent = find_opponent(player_id, language)   # Look for an opponent if none
    if opponent is None:                            # is found add player_id to queue
        join_queue(player_id, language)
        return None
    opponent_id = opponent["player_id"]

    try:
        return start_match(player_id, opponent["player_id"], language)
    except Exception:
        join_queue(opponent_id, language) # XXX 
        raise

""" INVITE GAME HELPERS """

# reserve for intivte games 
def create_game(player_id: str, language: str) -> dict:
    """ Creates a game, its answer, and the creator's plays row
        (turn 1_). Only returns the new game row and never the
        answer. 'invite (shared by game_id) or 'match' (in pool) """
    if has_open_game(player_id):
        raise GameConflict("You have already have an open game")
    
    db = admin()

    # game_id is generated randomly by Postgres with gen_random_uuid()
    game = rows(db.table("game").insert({"status": "waiting"}).execute())[0]
    game_id = game["game_id"]

    try:
        word = pick_answer_word(language)
        db.table("answer").insert({"game_id": game_id, "word": word, "language": language}).execute()
        db.table("plays").insert({"game_id": game_id, "player_id": player_id, "turn_order":1}).execute()
    except Exception:
        # Since these inserts happen sequentially and not in a
        # single transaction upon failure we must undo the game
        db.table("game").delete().eq("game_id", game_id).execute()
        raise
    return game

""" GAME HELPERS """

def start_match(player_a: str, player_b: str, language: str) -> dict:
    """ Starts a match between two paired players from matchmaking. The turn order 
        is randomly assined. Eventually, starts game once second player is seated """

    p1, p2 = random.sample([player_a, player_b], 2)
    game = insert_game(p1, language)

    try:
        return join_second_player(game["game_id"], p2)
    except Exception: # If joining a second player fails 
        (admin().table("game")              # DELETE
         .delete()                          # FROM game
         .eq("game_id", game["game_id"])    # WHERE game_id = game_id
         .execute())
        raise    

# NOTE: this function is designed to be reused with
def insert_game(player_id: str, language: str) -> dict:
    """ Inserts a game into games table. Adds the player with turn order 1 to the
        plays table. Player two needs to get added with join_second_player() """

    db = admin()

    game = rows(db.table("game")
                .insert({"status": "waiting"})
                .execute())[0]
    game_id = game["game_id"] # game_id is generated randomly by Postgres with gen_random_uuid()

    try:
        word = pick_answer_word(language)
        (db.table("answer")                                                         # INSERT INTO answer
         .insert({"game_id": game_id, "word": word, "language": language})          # (game_id, word, langauge)
         .execute())
        (db.table("plays")                                                          # INSERT INTO plays
         .insert({"game_id": game_id, "player_id": player_id, "turn_order": 1})     # (game_id, player_id, turn_order)
         .execute())
    except Exception:
        # Since these inserts happen sequentially and not in a
        # single transaction upon failure we must undo the game
        (db.table("game")           # DELETE
         .delete()                  # FROM game
         .eq("game_id", game_id)    # WHERE game_id = game_id
         .execute())
        raise
    return game

""" PLAYER TWO HELPERS """

def join_second_player(game_id: str, player_id: str) -> dict:
    """ Writes the second player into the game. Once a game has two player then
        the game status is upgraded to 'started' """

    db = admin()

    try:
        (db.table("plays")                                                      # INSERT INTO plays
         .insert({"game_id": game_id, "player_id": player_id, "turn_order": 2}) # (game_id, player_id, turn_order)
         .execute())
    except APIError as e: # Insertions failed 
        if e.code == "23505": # unique_violation
            raise GameConflict("This game is full") # Race case: Since game has not yet been set to 'started'. When two players
        raise                                       # join an invite at the same time, one of the insertions will fail.

    updated = rows(db.table("game")                 # UPDATE game
                   .update({"status": "started"})   # SET status 'started'
                   .eq("game_id", game_id)          # WHERE game_id = game_id
                   .eq("status", "waiting")         #   AND status = 'waiting'
                   .execute())
    if not updated: # This happens when the match is cancelled while P2 is joinging
        if get_game_row(game_id) is None:
            raise GameNotFound(game_id) # Match was cancelled
    return updated[0]

""" END PLAYERS TWO HELPERS """


def cancel_game(game_id: str, player_id: str) -> None:
    """ Deletes a game that has status 'waiting' only the owner can cancel """
    db = admin()

    game = get_game_row(game_id)
    if game is None:
        raise GameNotFound(game_id)

    # Find the host of the game (player with turn = 1 for invite games)
    host = rows(db.table("plays")       # SELECT player_id
                .select("player_id")    # FROM plays
                .eq("game_id", game_id) # WHERE game_id = game_id
                .eq("turn_order", 1)    #   AND turn_order = 1
                .execute())

    if not host or host[0]["player_id"] != player_id:       # If the player_id does not match the host
        raise GameForbidden(game_id)                        # then they do not have permission to cancel
    if game["status"] != "waiting":                         # the game. Similarly, if the game has status
        raise GameConflict("you cannot cancel this game")    # 'started' nobody has permission to cancel

    deleted = rows(db.table("game")         # DELETE
                   .delete()                # FROM game
                   .eq("game_id", game_id)  # WHERE game_id = game_id
                   .eq("status", "waiting") #   AND status = 'waiting'
                   .execute())

    if not deleted:                                         # If the game status is updated to 'started' between when we
        raise GameConflict("game already in progress")      # checked permissions and took action then deletion will fail

def has_open_game(player_id: str) -> bool:
    """ A player may only be in one game at a time. Matchmaking opens a game.  """
    plays = rows(admin().table("plays")         # SELECT game_id
                 .select("game_id")             # FROM plays
                 .eq("player_id", player_id)    # WHERE player_id == player_id
                 .execute())
    if not plays:
        return False

    open_games = rows(admin().table("game")                             # SELECT game_id
                      .select("game_id")                                # FROM game
                      .in_("game_id", [p["game_id"] for p in plays])    # WHERE game_id IN ( [p["game_id"] for p in plays])
                      .in_("status", OPEN_STATUS)                       #   AND status IN ('waiting', 'in_progress')
                      .limit(1)                                         # LIMIT 1
                      .execute())
    return len(open_games) > 0

def get_game_row(game_id: str) -> dict | None:
    res = admin().table("game").select("*").eq("game_id", game_id).execute()
    data = rows(res)
    return data[0] if data else None

def is_player_in_game(game_id: str, player_id: str) -> bool:
    """ Checks if player is in this specified game """
    res = (admin().table("plays")       # SELECT player_id
           .select("player_id")         # FROM plays
           .eq("game_id", game_id)      # WHERE game_id == game_id
           .eq("player_id", player_id)  #   AND player_id == player_id
           .execute())
    return len(rows(res)) > 0

def join_game(game_id: str, player_id: str) -> dict:
    """Adds second player to game with turn 2. Reuturns game row."""
    db = admin()

    game = get_game_row(game_id)
    if game is None:
        raise GameNotFound(game_id)
    if game["status"] != "waiting":
        raise GameConflict("This game is already in progress")  # The game has already been set to "started"
    if is_player_in_game(game_id, player_id):
        raise GameConflict("You are already in this game")
    if has_open_game(player_id):
        raise GameConflict("You cannot join two games") # XXX: This might create some ambiguity. Being in matchmaking opens
                                                        # a game, but that might be unclear to the player a solution might
                                                        # be to delay opening games until two players are paired. 

    try:
        db.table("plays").insert({"game_id": game_id, "player_id": player_id, "turn_order": 2}).execute()
    except APIError as e:
        if e.code == "23505": # unique_violation
            raise GameConflict("This game is full") # The game has not yet been set to "started". Race case
        raise
    updated = rows(db.table("game")                 # UPDATE status -> 'started'
                   .update({"status": "started"})   # FROM game
                   .eq("game_id", game_id)          # WHERE game_id = game_id
                   .eq("status", "waiting")         #   AND status = 'waiting'
                   .execute())

    if not updated:
        # Game was cancelled while P2 joins
        if get_game_row(game_id) is None:   # cancelled games are deleted
            raise GameNotFound(game_id)
        raise GameConflict("This game is in progress")
    return updated[0]

def whose_turn(players: list[dict], guesses: list[dict]) -> str | None:
    """ P1 will always go first, then turns will alternate. """
    next_order = len(guesses) % 2 + 1
    for p in players:
        if p["turn_order"] == next_order:
            return p["player_id"]
    return None # Player 2 hasn't joined yet

def get_game_state(game_id: str, player_id: str) -> dict:
    """ Returns the game state. The answer word is not returned until the game status 
        as been set the 'finished'. """
    db = admin()

    game = get_game_row(game_id)
    if game is None:
        raise GameNotFound(game_id)

    # players, with username pulled from the player table via FK
    plays = rows(db.table("plays")                                              # SELECT player_id, turn_order, results, player(username)
                 .select("player_id, turn_order, results, player(username)")    # FROM plays
                 .eq("game_id", game_id)                                        # WHERE game_id == game_id
                 .order("turn_order")                                           # ORDER BY turn_order
                 .execute())
    if player_id not in {p["player_id"] for p in plays}:
        raise GameForbidden(game_id)

    players = [{"player_id": p["player_id"],
                "username": (p.get("player") or {}).get("username"),
                "turn_order": p["turn_order"],
                "result": p["results"]}
                for p in plays]

    finished = game["status"] == "finished"

    answer = rows(db.table("answer")
                  .select("language, word" if finished else "language")
                  .eq("game_id", game_id)
                  .execute())

    guesses = rows(db.table("guess")
                   .select("attempt_num, player_id, word, feedback, made_at")
                   .eq("game_id", game_id)
                   .order("attempt_num")
                   .execute())

    state = {
        "game_id": game["game_id"],
        "status": game["status"],
        "created_at": game["created_at"],
        "ended_at": game["ended_at"],
        "language": answer[0]["language"] if answer else None,
        "players": players,
        "guesses": guesses,
        "current_turn" : whose_turn(players, guesses) if game["status"] == "started" else None,
    }
    if finished and answer:
        state["answer"] = answer[0]["word"]
    return state