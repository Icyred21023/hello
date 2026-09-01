import math
import json
import helpers

p = helpers.create_path("hero_data_keys.json")
data = helpers.load_json(p)
data = data['data']['items']
p = helpers.create_path("mvp_index.json")
mvp_index = helpers.load_json(p)
mvp_dict = mvp_index[0]['Rows']['mvp_index']
default_standard = mvp_dict['DefaultStandardScore']
standard_list = mvp_dict['StandardScore']

names = ['hawkeye', 'groot']

one = None
for name in names:
    hero_key = None
    for dicty in data:
        n = dicty["name"]
        n = n.lower()
        if n == name:
            hero_key = dicty["key"]
            break
    if hero_key is None:
        print(f"Hero key not found for player: {name}")
        break
    else:
        standard_score = None
        for standard in standard_list:
            if standard['Key'] == hero_key:
                standard_score = standard['Value']
                break
        if standard_score is None:
            print(f"Standard score not found for hero key: {hero_key}")
            standard_score = default_standard
    if one is None:
        name1 = name
        std1 = standard_score
        one = True
    else:
        name2 = name
        std2 = standard_score
heroes = {
 name1: dict(kills=15,deaths=7,assists=1,damage=12023,healing=0,damage_taken=6648,final_hits=10,std=std1),
 name2: dict(kills=11,deaths=7,assists=2,damage=8899,healing=0,damage_taken=33511,final_hits=6,std=std2)
}

# heroes = {
#  "namor": dict(kills=31,deaths=9,assists=2,damage=31157,healing=0,damage_taken=10624,final_hits=20,std=748),
#  "wolverine": dict(kills=38,deaths=9,assists=0,damage=26119,healing=470,damage_taken=10624,final_hits=17,std=639)
# }

def mvp(h, p=1.0):
    raw = (
         h["damage"]*1.0 + h["healing"]*1.2 +
           h["damage_taken"]*0.6)
    score = ((raw / (h["std"]**p)) ) *( h["kills"] * 1.2 + h["final_hits"]*2.4 + h["assists"]*0.6 - h["deaths"]*0.4)
           
    return score

for p in (1.0,0.8):
    print(p, {k: mvp(v, p) for k, v in heroes.items()})
