from datetime import datetime
class Guess:
    def __init__(self, attempt_number, username):
        self.attempt_number = attempt_number
        self.username = username
        self.guessed_at = datetime.now()
