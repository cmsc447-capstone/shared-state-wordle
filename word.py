class Word:
    def __init__(self, word, is_answer):
        self.word = word            # The actual word string
        self.is_answer = is_answer  # True if valid as the correct answer, False if only a guess
