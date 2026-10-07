from datetime import datetime
class Player:
    def __init__(self, player_id, username):
        self.player_id = player_id
        self.username = username
        self.created_at = datetime.now()
