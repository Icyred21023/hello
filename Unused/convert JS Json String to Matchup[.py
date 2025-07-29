import json
import os

def parse():
    path = r"C:\Users\Corey\Desktop\py\marvel_tracker\newmatchup.json"
    path2 = r"C:\Users\Corey\Desktop\py\marvel_tracker\newmatchupPYTHON.json"
    with open(path, "r") as f:
        data = json.load(f)
    named_dict = {item["name"]: item for item in data}
    with open(path2, "w", encoding="utf-8") as f:
        json.dump(named_dict, f, indent=2)

parse()

