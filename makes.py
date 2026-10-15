class Makes:
    def __init__(self, player_id, username, attempt_number):
        self.player_id = player_id          # foreign key to Player
        self.username = username            # foreign key to Guess 
        self.attempt_number = attempt_number # foreign key to Guess 
