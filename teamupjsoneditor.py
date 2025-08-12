import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, "teamups.json")


with open(matchup_path, encoding="utf-8") as f:
    data = json.load(f)
jss = {"TeamUps":{}}
for char in data["TeamUps"]:
    title = data["TeamUps"][char]['teamup']
    characters = data["TeamUps"][char]['characters']
    new = {"score": 1.0, "teamup": title, "characters": characters}
    jss["TeamUps"][char] = new
matchup_path2 = os.path.join(script_dir, "teamups2.json")
with open(matchup_path2, 'w', encoding='utf-8') as f:
    json.dump(jss, f, indent=4, ensure_ascii=False)