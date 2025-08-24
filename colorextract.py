import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'debug','alldata.json')
with open(data_path, 'r') as file:
    data = json.load(file)

color_dict = {}
for key in data:
    print(f"Processing key: {key}")
    if 'data' not in data[key] or 'segments' not in data[key]['data']:
        print(f"Skipping key {key} due to missing 'data' or 'segments'")
        continue
    segments = data[key]['data']['segments']
    for segment in segments:
        if segment['type'] != 'hero':
            continue
        name = segment['metadata']['name']
        color = segment['metadata']['color']
        if name not in color_dict:
            color_dict[name] = color

output_path = os.path.join(script_dir, 'colors.json')
with open(output_path, 'w', encoding='utf-8') as file:
    json.dump(color_dict, file, indent=4,ensure_ascii=False)
