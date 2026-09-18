import helpers
import os
import json, gzip
import time

def build_data():
    all_matches = []
    path = helpers.create_path("_hero_map.json", "debug")
    hero_map = helpers.load_json(path)
    name = '_all_resultsJSONfull.json'
    path = helpers.create_path(name, 'debug')
    data = helpers.load_json(path)
    if data is None:
        print(f"Failed to load JSON from {path}")
        return
    print(f"Loaded {len(data)} entries from {name}")
    dataset = {}
    for index, key in enumerate(data):
        print(f"{index+1}/{len(data)}: Processing match {key}")
        match_data = {'match_id': key, 'team_0': {'heroes': [], 'swaps': [], 'stats': []}, 'team_1': {'heroes': [], 'swaps': [], 'stats': []}, 'winner': None}
        winner = None
        entry = data[key]['match_details']
        players = entry['match_players']
        for player in players:
          team = player['camp']
          win = player['is_win']
          if winner is None:
              winner = 0 if not win and team == 1 else (1 if not win else team)

          # Stats for the player
          stats = {
              'kills': player['kills'],
              'deaths': player['deaths'],
              'assists': player['assists'],
              'damage': player['total_hero_damage'],
              'healing': player['total_hero_heal']
          }

          # -------------------------
          # Find main hero (longest played)
          # -------------------------
          heroid = str(player['cur_hero_id'])
          if heroid == '1054':   # remap edge cases
              heroid = '1044'
          elif heroid == '0':
                playerer = player['player_heroes']
                if not playerer:
                    continue
                timec = -1
                hero_longest = ''
                for item in playerer:
                    heroid = str(item['hero_id'])
                    if heroid == '1054':
                        heroid = '1044'
                    time = item['play_time']
                    if time > timec:
                        timec = time
                        hero_longest = heroid
                heroid = hero_longest

          playerer = player['player_heroes']
          

          heroname = hero_map[heroid]['name']
          match_data[f'team_{team}']['heroes'].append(heroname)

          # -------------------------
          # Collect swaps (just names, empty if none)
          # -------------------------
          swaps = []
          if playerer:
              for item in playerer:
                  hid = str(item['hero_id'])
                  if hid == '1054':
                      hid = '1044'
                  hero_name = hero_map[hid]['name']
                  if hero_name == heroname:
                      continue  # skip the primary hero
                  swaps.append(hero_name)

          match_data[f'team_{team}']['swaps'].append(swaps)  # always append (even empty)

          # -------------------------
          # Add stats
          # -------------------------
          match_data[f'team_{team}']['stats'].append(stats)

        match_data['winner'] = winner
        all_matches.append(match_data)
    save_path = helpers.create_path('_all_matches_TRAIN.json', 'debug')
    helpers.save_json_compact(save_path, all_matches)
                


            
                
                

def compress():
  name = '_all_resultsJSONfull.json'
  path = helpers.create_path(name, 'debug')
  data = helpers.load_json(path)
  helpers.save_gz(path, data)

def merge():
  file_names = ['_all_resultsJSON1.json',
                '_all_resultsJSON2.json',
                  '_all_resultsJSON3.json',
                    '_all_resultsJSON4.json',
                      '_all_resultsJSON5.json',
                        '_all_resultsJSON6.json',
                          '_all_resultsJSON7.json',
                            '_all_resultsJSON8.json',
                              '_all_resultsJSON9.json', 
                              '_all_resultsJSON91.json', 
                              '_all_resultsJSON92.json', 
                              '_all_resultsJSON93.json']

  paths = []
  for file_name in file_names:
      path = helpers.create_path(file_name, 'debug')
      if os.path.exists(path):
          paths.append(path)
      else:
          print(f"File not found: {path}")
  new_data = {}
  for index, path in enumerate(paths):
      # if '_all_resultsJSON93.json' in path:
      #     print('debugging')
      #     with open(path, 'r', encoding='utf-8') as f:
      #         content = f.read()
      #     error_char = 25308380
      #     window = 40  # Number of characters before and after to print
      #     start = max(0, error_char - window)
      #     end = min(len(content), error_char + window)

      #     print(content[start:end])
      #     time.sleep(100)
      data = helpers.load_json(path)
      
      if data is None:
          print(f"     Failed to load JSON from {path}")
          break
      else:
          print(f"     Loaded {file_names[index]}. Merging data...")
      new_data.update(data)
      print(f"{index}: Merged {len(data)} entries from {file_names[index]}. Total entries now: {len(new_data)}")
  save_path = helpers.create_path('_all_resultsJSONfull.json', 'debug')
  helpers.save_json_compact(save_path, new_data)


build_data()