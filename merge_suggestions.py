from matchups4 import TeamResult, TeamMember, Suggestion
import copy

def add_alt_suggestions(base_result: TeamResult, secondary_result: TeamResult,red_result: TeamResult) -> TeamResult:
    # Add alt suggestions to each blue member
    for i in range(1, 7):
        base_member = getattr(base_result, str(i), None)
        second_member = getattr(secondary_result, str(i), None)
        if base_member and second_member:
            base_member.alt_suggestion = second_member.suggestion

    # Build alt blue team from alt suggestions
    alt_blue_team = []
    for i in range(1, 7):
        second_member = getattr(secondary_result, str(i), None)
        if second_member:
            alt_blue_team.append(second_member.character)

    # Evaluate red team against alt blue team, and store alt_score
    for i in range(1, 7):
        red_member = getattr(red_result, str(i), None)
        if red_member is None or red_member.character is None or not red_member.suggestion:
            continue

        red_char_copy = copy.deepcopy(red_member.character)
        red_char_copy.evaluate_vs_team(alt_blue_team)
        red_member.suggestion.alt_score = red_char_copy.matchup_score
        red_member.suggestion.priority = red_char_copy.matchup_score

    return base_result