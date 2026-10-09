from datetime import datetime
class Game:
    def __init__(self, game_id, target_word, player1_id, player2_id, 
                 winner_id, status, max_turns):

        """
        Some of these, like target_word, can probably be deleted because
        they're going to be member variables of other classes, instead of 
        belonging to game, based on the more recent (10/8/26) ER_Diagram
        """

        self.game_id = game_id
        self.target_word = target_word
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.winner_id = winner_id
        self.status = status
        self.max_turns = max_turns
        self.started_at = datetime.now()
        self.ended_at = datetime.now() + 1
        """ended_at is obviously not given a correct value here, but I'm not 
        sure yet how we'll be detecting the end of the game"""
