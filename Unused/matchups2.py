import json
import os

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
    suggestions = []
    used_replacements = set(c.name for c in team1 + team2)

    old_team1_score = sum(c.matchup_score for c in team1)
    old_team2_score = sum(c.matchup_score for c in team2)

    for orig_char in team1:
        best_alt = None
        best_team_delta = float("-inf")

        for candidate in character_pool.values():
            if candidate.name in used_replacements:
                continue
            if candidate.role != orig_char.role:
                continue

            # Simulate new team1
            new_team1 = [c for c in team1 if c.name != orig_char.name] + [candidate]

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
            suggestions.append({
                "replace": orig_char.name,
                "with": best_alt.name,
                "old_score": orig_char.matchup_score,
                "new_score": best_alt.matchup_score,
                "team_gain": best_team_delta
            })

    # Sort and return top 3 best suggestions
    suggestions.sort(key=lambda x: -x["team_gain"])
    return suggestions[:top_n]





# ====== TEST/USAGE EXAMPLE BELOW (delete or comment when importing) ======
#if __name__ == "__main__":
def counters(red, blue):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matchup_path = os.path.join(script_dir, "matchup.json")
    character_pool = load_characters(matchup_path)

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
    print("\nSuggested replacements (maximized team score):")
    if suggestions:
        for s in suggestions:
            print(f"- {s['replace']} ➜ {s['with']} "
                  f"(individual: {s['old_score']} ➜ {s['new_score']}, "
                  f"team gain: {s['team_gain']:+.1f})")
    else:
        print("✅ No replacements found that improve team performance.")
    # Apply suggestions to build improved team1
    updated_team1 = []
    
    for char in team1:
        replacement = next((s for s in suggestions if s["replace"] == char.name), None)
        if replacement:
            # Use replacement character
            replacement_char = character_pool[replacement["with"]]
            updated_team1.append(replacement_char)
        else:
            updated_team1.append(char)
    
    # Re-evaluate both teams with updated team1
    for c in updated_team1:
        c.evaluate_vs_team(team2)
    for c in team2:
        c.evaluate_vs_team(updated_team1)
    
    new_team1_score = sum(c.matchup_score for c in updated_team1)
    new_team2_score = sum(c.matchup_score for c in team2)
    
    print("\n📈 Team score after applying suggestions:")
    print(f"  New Team 1 Score: {new_team1_score}")
    print(f"  Team 2 Score:     {new_team2_score}")
    print(f"  Net Team Advantage: {new_team1_score - new_team2_score:+.1f}")
    