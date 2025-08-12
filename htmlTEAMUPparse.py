from bs4 import BeautifulSoup
import json
from pathlib import Path
from collections import defaultdict
import re
import os
import config
from icyred_matchup_logic import load_characters

html_path = Path(r"C:\Users\Corey\Desktop\-Marvel3\-Marvel2\marvel_tracker_V5/Team-Ups.html")
html = html_path.read_text(encoding="utf-8", errors="ignore")
script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, config.MATCHUP)

character_pool = load_characters(matchup_path)
with open(matchup_path, encoding="utf-8") as f:
    data = json.load(f)

chars = [item for item in character_pool]
soup = BeautifulSoup(html, "html.parser")

def clean_text(t):
    import re
    return re.sub(r"\s+", " ", (t or "").strip())

# Find all h2 team-up headers
h2s = soup.find_all("h2")
teamups = {}
anchor_to_secondaries = defaultdict(list)

def extract_heroes(block):
    names = []
    for a in block.find_all("a"):
        title = a.get("title")
        if title and title.lower() not in {"edit", "file", "image"}:
            if any(ch.isalpha() for ch in title):
                names.append(title.strip())
    # dedupe
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            out.append(n); seen.add(n)
    return out

def parse_perks(block):
    perks = {}
    smalls = block.find_all(["small"])
    blob = "\n".join(sm.get_text("\n", strip=True) for sm in smalls if sm.get_text(strip=True))
    for line in blob.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = clean_text(k).upper()
            v = clean_text(v)
            perks[k] = v
    return perks

for i, h2 in enumerate(h2s):
    span = h2.find("span", class_="mw-headline")
    if not span: 
        continue
    teamup_name = clean_text(span.get_text())
    # collect content until next h2
    content_nodes = []
    node = h2.next_sibling
    while node and not (getattr(node, "name", None) == "h2"):
        content_nodes.append(node)
        node = node.next_sibling
    section = BeautifulSoup("".join(str(n) for n in content_nodes), "html.parser")

    # find "TEAM-UP ANCHOR"
    anchor_label = section.find(string=re.compile(r"TEAM-?UP\s+ANCHOR", re.I))
    anchor_hero = None
    if anchor_label:
        all_desc = list(section.descendants)
        try:
            idx = all_desc.index(anchor_label)
        except ValueError:
            idx = None
        if idx is not None:
            for k in range(idx-1, -1, -1):
                el = all_desc[k]
                if getattr(el, "name", None) == "a" and el.get("title"):
                    t = el.get("title").strip()
                    if t.lower() not in {"file", "image", "edit"}:
                        anchor_hero = t
                        break

    heroes = extract_heroes(section)
    secondaries = [h for h in heroes if h != anchor_hero]

    perks = parse_perks(section)
    anchor_perks = {}
    secondary_perks = {}
    for k, v in perks.items():
        if "TEAM-UP BONUS" in k or k == "KEY":
            anchor_perks[k] = v
        else:
            secondary_perks[k] = v

    if anchor_hero or secondaries or perks:
        teamups[anchor_hero] = {
            "teamup": teamup_name,
            "characters": {sec: 1.0 for sec in secondaries if sec in chars},
            
        }
        if anchor_hero:
            anchor_to_secondaries[anchor_hero].extend(secondaries)

anchor_to_secondaries = {k: sorted(set(v)) for k, v in anchor_to_secondaries.items()}
result = {"TeamUps": teamups, "Index": {"anchor_to_secondaries": anchor_to_secondaries}}

out_path = Path(r"C:\Users\Corey\Desktop\-Marvel3\-Marvel2\marvel_tracker_V5\teamups.json")
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Found {len(teamups)} sections with data.")
print(f"Saved JSON to {out_path}")
