import json

class Character:
    def __init__(self, data):
        self.name = data["name"]
        self.role = data["role"]
        self.countered_by = [entry["name"] for entry in data.get("counterPicks", [])]
        self.matchup_score = 0
        self.counters_given = []
        self.counters_received = []

    def evaluate_vs_team(self, enemy_team):
        self.matchup_score = 0
        self.counters_given = []
        self.counters_received = []

        for enemy in enemy_team:
            # ❌ if this hero is countered by an enemy
            if enemy.name in self.countered_by:
                self.matchup_score -= 1
                self.counters_received.append(enemy.name)

            # ✅ if this hero counters an enemy (check if *they* are countered by self)
            if self.name in enemy.countered_by:
                self.matchup_score += 1
                self.counters_given.append(enemy.name)



def load_characters(filename):
    with open(filename, "r") as f:
        raw_data = json.load(f)
    return {name: Character(data) for name, data in raw_data.items()}


def build_team(names, character_pool):
    return [character_pool[name] for name in names if name in character_pool]


def evaluate_team_matchups(team1, team2):
    for char in team1:
        char.evaluate_vs_team(team2)
    for char in team2:
        char.evaluate_vs_team(team1)

    score1 = sum(c.matchup_score for c in team1)
    score2 = sum(c.matchup_score for c in team2)
    print("\n🔍 Team 1 Individual Matchup Scores:")
    return score1, score2


def suggest_replacements(team1, team2, character_pool, top_n=3):
    worst = sorted(team1, key=lambda c: c.matchup_score)[:top_n]
    suggestions = {}
    used_replacements = set(c.name for c in team1 + team2)

    # Calculate current total score
    old_team1_score = sum(c.matchup_score for c in team1)
    old_team2_score = sum(c.matchup_score for c in team2)

    for bad_char in worst:
        best_alt = None
        best_team_delta = float("-inf")

        for candidate in character_pool.values():
            if candidate.name in used_replacements:
                continue
            if candidate.role != bad_char.role:
                continue

            # Simulate new team with candidate
            new_team1 = [c for c in team1 if c.name != bad_char.name] + [candidate]
            # Re-evaluate matchups
            for c in new_team1:
                c.evaluate_vs_team(team2)
            for c in team2:
                c.evaluate_vs_team(new_team1)

            new_team1_score = sum(c.matchup_score for c in new_team1)
            new_team2_score = sum(c.matchup_score for c in team2)

            team_score_delta = (new_team1_score - new_team2_score) - (old_team1_score - old_team2_score)

            if team_score_delta > best_team_delta:
                best_team_delta = team_score_delta
                best_alt = candidate

        if best_alt:
            used_replacements.add(best_alt.name)
            suggestions[bad_char.name] = {
                "replace_with": best_alt.name,
                "old_score": bad_char.matchup_score,
                "new_score": best_alt.matchup_score,
                "team_score_gain": best_team_delta
            }

    return suggestions





# ====== TEST/USAGE EXAMPLE BELOW (delete or comment when importing) ======
#if __name__ == "__main__":
def counterss(red, blue):
    character_pool = load_characters("matchup.json")

    # team1_names = ["Iron Man", "Ultron", "Rocket", "Luna", "Storm", "Venom"]
    # team2_names = ["Groot", "Hela", "Doctor Strange", "Iron Fist", "Hawkeye", "Magneto"]
    # print(f"My Team: {team1_names}")
    # print(f"Enemy Team: {team2_names}")
    team1 = build_team(red, character_pool)
    team2 = build_team(blue, character_pool)

    score1, score2 = evaluate_team_matchups(team1, team2)
    print("\n🔍 Team 1 Individual Matchup Scores:")
    for char in team1:
        print(f"\n🧩 {char.name} — Score: {char.matchup_score}")
        if char.counters_given:
            print(f"  ✅ Counters: {', '.join(char.counters_given)}")
        if char.counters_received:
            print(f"  ❌ Countered by: {', '.join(char.counters_received)}")
        if not char.counters_given and not char.counters_received:
            print("  ⚪ Neutral matchup")
    
    

    print(f"Team 1 Score: {score1}")
    print(f"Team 2 Score: {score2}")

    suggestions = suggest_replacements(team1, team2, character_pool)
    print("\nSuggested replacements for worst matchups (team-optimized):")
    if suggestions:
        for bad, change in suggestions.items():
            print(f"- {bad} ➜ {change['replace_with']} "
                  f"(score: {change['old_score']} ➜ {change['new_score']}, "
                  f"team improvement: {change['team_score_gain']:+.1f})")
    else:
        print("✅ No replacements found that improve team performance.")
    