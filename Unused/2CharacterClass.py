class Character:
    def __init__(self, name, data):
        self.name = name
        self.counters = set(data.get("Counters", []))
        self.matchup_score = 0  # will be calculated later

    def evaluate_matchup(self, enemy_team):
        # Reset score
        self.matchup_score = 0
        for enemy in enemy_team:
            if self.name in enemy.counters:
                self.matchup_score -= 1  # This character is being countered
            if enemy.name in self.counters:
                self.matchup_score += 1  # This character counters someone
