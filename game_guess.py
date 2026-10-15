class Game_Guess:
    def __init__(self, game_id, username, attempt_number):
        self.game_id = game_id              # Foreign key to game
        self.username = username            # foreign key to guess
        self.attempt_number = attempt_number # foreign key to guess
