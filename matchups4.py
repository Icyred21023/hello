import json
import os
from copy import deepcopy


class Suggestion:
    def __init__(self, original, replacement, orig_score, new_score, priority, alt_score=None):
        self.original = original
        self.replacement = replacement
        self.orig_score = orig_score
        self.new_score = new_score
        self.priority = priority
        self.alt_score = alt_score  # optional third comparison score

class TeamMember:
    def __init__(self, character, suggestion=None, alt_suggestion=None):
        self.character = character
        self.suggestion = suggestion  # From matchups4
        self.alt_suggestion = alt_suggestion  # From chatsitecopy

class TeamResult:
    def __init__(self, members, original_score, updated_score):
        for i, member in enumerate(members, 1):
            setattr(self, str(i), member)
        self.original_score = original_score
        self.updated_score = updated_score

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
            if enemy.name in self.countered_by:
                self.matchup_score -= 1
                self.counters_received.append(enemy.name)
            if self.name in enemy.countered_by:
                self.matchup_score += 1
                self.counters_given.append(enemy.name)

def load_characters(filename):
    with open(filename, "r") as f:
        raw_data = json.load(f)
    return {
        name: Character(data)
        for name, data in raw_data.items()
        if name != "Unknown"
    }

def build_team(names, character_pool):
    missing = [name for name in names if name not in character_pool]
    if missing:
        print("⚠️ Missing characters in character_pool:", missing)
    return [character_pool[name] for name in names if name in character_pool]

def evaluate_team_matchups(team1, team2):
    for char in team1:
        char.evaluate_vs_team(team2)
    for char in team2:
        char.evaluate_vs_team(team1)
    return sum(c.matchup_score for c in team1), sum(c.matchup_score for c in team2)

def find_best_replacement(orig_char, current_team, enemy_team, character_pool, used_names):
    best_alt = None
    best_gain = float("-inf")
    orig_score = orig_char.matchup_score

    for candidate in character_pool.values():
        if candidate.name in used_names or candidate.role != orig_char.role:
            continue
        new_team = deepcopy([c for c in current_team if c.name != orig_char.name] + [candidate])
        enemy_team_copy = deepcopy(enemy_team)

        for c in new_team:
            c.evaluate_vs_team(enemy_team_copy)
        for c in enemy_team_copy:
            c.evaluate_vs_team(new_team)
        new_team_score = sum(c.matchup_score for c in new_team)
        new_enemy_score = sum(c.matchup_score for c in enemy_team)

        current_team_score = sum(c.matchup_score for c in current_team)
        current_enemy_score = sum(c.matchup_score for c in enemy_team)

        gain = (new_team_score - new_enemy_score) - (current_team_score - current_enemy_score)
        if gain > best_gain:
            best_gain = gain
            best_alt = deepcopy(candidate)
            best_alt.evaluate_vs_team(enemy_team)
    return best_alt, best_gain

def iterative_suggestions(team1, team2, character_pool):
    used_names = set(c.name for c in team1)
    current_team = deepcopy(team1)
    original_score, _ = evaluate_team_matchups(current_team, team2)
    suggestions = []
    priority = 1

    for _ in range(6):
        # 🔄 Rebuild slot-to-character map fresh each round to avoid stale references
        slot_char_map = [(i, c) for i, c in enumerate(current_team)]

        best_overall = None
        best_gain = float("-inf")
        best_orig = None
        best_idx = None

        for idx, orig_char in slot_char_map:
            #if any(s is not None and s.original == orig_char.name for _, s in suggestions):
                #continue

            alt, gain = find_best_replacement(orig_char, current_team, team2, character_pool, used_names)

            if alt and gain > best_gain:
                best_overall = alt
                best_gain = gain
                best_orig = orig_char
                best_idx = idx

        if best_overall and best_gain > 0:
            suggestion = Suggestion(
                best_orig.name, best_overall.name,
                best_orig.matchup_score, best_overall.matchup_score,
                priority
            )
            priority += 1
            current_team[best_idx] = best_overall
            suggestions.append((best_idx, suggestion))
            used_names.add(best_overall.name)
        elif best_idx is not None:
            # No improvement — still record original info
            suggestions.append((best_idx, Suggestion(
                best_orig.name, best_orig.name,
                best_orig.matchup_score, best_orig.matchup_score,
                None
            )))

    final_score, _ = evaluate_team_matchups(current_team, team2)

    members = []
    for i, char in enumerate(current_team):
        sug = next((s for idx, s in suggestions if idx == i), None)
        members.append(TeamMember(char, sug))

    # Evaluate red team against original blue team (team1)
    for red_char in team2:
        red_char.evaluate_vs_team(team1)
    red_scores_orig = {c.name: c.matchup_score for c in team2}

    # Evaluate red team against final blue team (current_team)
    for red_char in team2:
        red_char.evaluate_vs_team(current_team)
    red_scores_sugg = {c.name: c.matchup_score for c in team2}

    # Build red members with both scores
    red_members = []
    for red_char in team2:
        suggestion = Suggestion(
            red_char.name, red_char.name,
            red_scores_orig[red_char.name],
            red_scores_sugg[red_char.name],
            None
        )
        red_members.append(TeamMember(red_char, suggestion))

    print("Red team member count:", len(red_members))
    for m in red_members:
        print(" -", m.character.name)

    red_team_result = TeamResult(red_members, sum(red_scores_orig.values()), sum(red_scores_sugg.values()))
    return TeamResult(members, original_score, final_score), red_team_result

def iterative_suggestions2(team1, team2, character_pool):
    used_names = set(c.name for c in team1)
    current_team = deepcopy(team1)
    original_score, _ = evaluate_team_matchups(current_team, team2)
    suggestions = []
    priority = 1

    # Store mapping of original slot -> current character
    slot_char_map = [(i, c) for i, c in enumerate(current_team)]

    for _ in range(6):
        best_overall = None
        best_gain = float("-inf")
        best_orig = None
        best_idx = None

        for idx, orig_char in slot_char_map:
            if any(s.original == orig_char.name for _, s in suggestions):
                continue
            alt, gain = find_best_replacement(orig_char, current_team, team2, character_pool, used_names)
            if alt and gain > best_gain:
                best_overall = alt
                best_gain = gain
                best_orig = orig_char
                best_idx = idx

        if best_overall:
            suggestion = Suggestion(best_orig.name, best_overall.name,
                                    best_orig.matchup_score, best_overall.matchup_score, priority)
            priority += 1
            current_team[best_idx] = best_overall
            suggestions.append((best_idx, suggestion))
            used_names.add(best_overall.name)

    final_score, _ = evaluate_team_matchups(current_team, team2)

    # Build members while preserving correct suggestion per slot
    members = []
    for i, char in enumerate(current_team):
        sug = next((s for idx, s in suggestions if idx == i), None)
        members.append(TeamMember(char, sug))

    blue_team_result = TeamResult(members, original_score, final_score)
    red_members = [TeamMember(c, None) for c in team2]
    print("Red team member count:", len(red_members))  # Should always be 6
    for m in red_members:
        print(" -", m.character.name)

    score, _ = evaluate_team_matchups(team2, current_team)
    red_team_result = TeamResult(red_members, score, score)
    return blue_team_result, red_team_result


def counters(red, blue,matchup_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    #matchup_path = os.path.join(script_dir, "matchup.json")
    character_pool = load_characters(matchup_path)

    team1 = build_team(red, character_pool)
    team2 = build_team(blue, character_pool)
    blue_result, red_result = iterative_suggestions(team1, team2, character_pool)

    print("🔵 ORIGINAL BLUE TEAM:")
    for i, name in enumerate(red, 1):
        print(f"  {i}. {name}")
    print(f"  Total Score: {blue_result.original_score}\n")

    print("🔁 REPLACEMENT SUGGESTIONS:")
    for i in range(1, 7):
        member = getattr(blue_result, str(i))
        s = member.suggestion
        if s:
            print(f"  {s.priority}. Replace {s.original} ➜ {s.replacement} "
                f"(Matchup Score: {s.orig_score} ➜ {s.new_score})")
        else:
            print(f"  {i}. No suggestion for {member.character.name}")

    print(f"\n✅ FINAL UPDATED BLUE TEAM SCORE: {blue_result.updated_score}")
    print(f"🟥 RED TEAM SCORE (Unchanged): {red_result.updated_score}")
    print(f"📊 Net Advantage: {blue_result.updated_score - red_result.updated_score:+.1f}")

    return blue_result, red_result




