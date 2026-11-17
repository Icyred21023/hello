



def build_enemy_dict(p):
    uid = p.get("uid", None)
    if uid is None:
        print(f"❌ RivalsData UID fetch failed for player '{p.get('name', 'Unknown')}' - UID is None.")
        return None
    name = p.get("name", None)
    icon = p.get("icon", None)
    import random
    random_value = random.randint(1000000000000000000, 9999999999999999999)
    enemy =  {
                "ai": False,
                "games": 0,
                "icon": str(icon) if icon else "Unknown",
                "losses": 0,
                "name": name,
                "proficiency": [],
                "rank": {
                    "level": 23,
                    "score": 5270.8314193538135
                },
                "side": 0,
                "team_id": str(random_value),
                "top_heroes": [],
                "uid": str(uid),
                "wins": 0
            }
    return enemy
    


def make_bynames_live_match(players):
    data = {"players": {}}
    idx = 0
    
    idx += 1
    for player in players:
        d = build_enemy_dict(player)
        data["players"][idx] = d
        idx += 1
    return data