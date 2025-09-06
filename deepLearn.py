import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time, json, os, subprocess, re
import config
import tracker_lookup
if not config.mobile_mode:
    import psutil

PY_DIR = os.path.dirname(os.path.abspath(__file__))

def create_path(file, folder=""):
    pa = os.path.join(PY_DIR, folder, file)
    return pa
    
def load_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data
    
def save_json(path,data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
from collections import defaultdict

def collapse_to_team_level(match_json, scale_to=6.0):
    """
    Convert parsed match JSON into team-level hero fraction vectors + winner label.
    Fractions are rescaled so each team sums to `scale_to` (default 6.0).
    """
    def aggregate_team(team):
        hero_fractions = defaultdict(float)
        for player in team:
            for hero_entry in player["heroes_played"]:
                frac = hero_entry.get("time_fraction", 0.0)
                if frac > 0:
                    hero = hero_entry["hero"]
                    hero_fractions[hero] += frac
        # rescale to sum = scale_to
        total = sum(hero_fractions.values())
        if total > 0:
            for hero in hero_fractions:
                hero_fractions[hero] *= (scale_to / total)
        return dict(hero_fractions)

    team0_vec = aggregate_team(match_json["team_0"])
    team1_vec = aggregate_team(match_json["team_1"])
    
    # Label: 1 if team_0 won, else 0
    label = 1 if match_json["winner"] == "team_0" else 0
    
    return {
        "match_id": match_json["match_id"],
        "team_0": team0_vec,
        "team_1": team1_vec,
        "label": label
    }

def parse_match_data(match_data):
    mid = match_data['data']['attributes']['id']
    winningTeamId = match_data['data']['metadata']['winningTeamId']
    segments = match_data['data']['segments']
    duration = match_data['data']['metadata']['duration']
    bParsingPlayer = False
    result = {"match_id": mid, "team_0": [], "team_1":[],  "winner": f"team_{winningTeamId}" }
    pid = 0
    for index, segment in enumerate(segments):
        if segment['type'] == 'player':
            if bParsingPlayer:
                playerdata = {"player_id": f"player_{pid}", "heroes_played": hero_list}
                result[f"team_{teamId}"].append(playerdata)
                pid += 1
                
                
            bParsingPlayer = True
            teamId = segment['metadata']['teamId']
            hero_list = []
        elif segment['type'] == 'hero':
            
            heroName = segment['metadata']['name']
            roleName = segment['metadata']['roleName']
            timePlayed = round(segment['stats']['timePlayed']['value'] / 1000, 2 )
            hero_temp = {"hero": heroName, "role": roleName, "time_fraction": round(timePlayed/duration,2)}
            hero_list.append(hero_temp)
    playerdata = {"player_id": f"player_{pid}", "heroes_played": hero_list}
    result[f"team_{teamId}"].append(playerdata)
    return result
            
def fetch_tracker_api(names):
    tracker_lookup.kill_selenium_chrome()
    season = config.season
    mode = "competitive"

    # --- NEW: pin UC to your installed Chrome major version ---
    chrome_major = tracker_lookup.get_chrome_major_version(default=138)
    print(f"Detected Chrome major version: {chrome_major}")

    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")  # Optional
    profile_path = os.path.join(os.environ["TEMP"], "selenium_admin_profile")
    os.makedirs(profile_path, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1,1")

    # IMPORTANT: pass version_main
    driver = uc.Chrome(options=options, version_main=chrome_major)

    # keep your tiny window behavior
    driver.set_window_position(-10000, 0)
    driver.set_window_size(1, 1)
    all_matches = []
    for ign in names:
        url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/ign/{ign}?mode={mode}&season={season}"
        try:
            driver.get(url)
            pre = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            raw_json = pre.text
            data = json.loads(raw_json)
            if "data" in data and not data["data"]:                      
                print(f"❌ No data found for {ign}: Season {season}")
                continue
            else:
                match_list = data['data']['matches']
                for match in match_list:
                    
                    match_id = match['attributes']['id']
                    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/{match_id}"
                    time.sleep(0.45)
                    driver.get(url)
                    pre = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "pre"))
                    )
                    raw_json = pre.text
                    match_data = json.loads(raw_json)
                    result = parse_match_data(match_data)
                    processed = collapse_to_team_level(result)
                    all_matches.append(processed)
    

        except Exception as e:
            print(f"❌ Error loading JSON for {ign}: {e}")
    return all_matches
    

# Example

        
        
        
pat1h = create_path("alldata.json","debug")
all_data = load_json(pat1h)
names = list(all_data.keys())[-15:]
all_matches = fetch_tracker_api(names)
save_json(create_path("matchdata.json","debug"), all_matches)

# Collect all heroes seen across dataset
hero_set = set()
for m in all_matches:
    hero_set.update(m["team_0"].keys())
    hero_set.update(m["team_1"].keys())

hero2id = {hero: i for i, hero in enumerate(sorted(hero_set))}

import numpy as np

def team_to_vector(team_dict, hero2id):
    vec = np.zeros(len(hero2id), dtype=np.float32)
    for hero, val in team_dict.items():
        vec[hero2id[hero]] = val
    return vec

X = []
y = []

for m in all_matches:
    team0_vec = team_to_vector(m["team_0"], hero2id)
    team1_vec = team_to_vector(m["team_1"], hero2id)
    match_vec = np.concatenate([team0_vec, team1_vec])
    X.append(match_vec)
    y.append(m["label"])

X = np.array(X, dtype=np.float32)
y = np.array(y, dtype=np.float32)

# ---------------------------
# sklearn baseline (still works)
# ---------------------------
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = LogisticRegression(max_iter=500)
model.fit(X_train, y_train)
print("Sklearn Validation accuracy:", model.score(X_val, y_val))

# ---------------------------
# torch version
# ---------------------------
import torch
from torch.utils.data import TensorDataset, DataLoader
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------
# Detect device (GPU if available)
# ---------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# Convert to tensors
X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train, dtype=torch.float32)
X_val_tensor = torch.tensor(X_val, dtype=torch.float32)
y_val_tensor = torch.tensor(y_val, dtype=torch.float32)

# Wrap in datasets
train_ds = TensorDataset(X_train_tensor, y_train_tensor)
val_ds = TensorDataset(X_val_tensor, y_val_tensor)

train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=32)

# Define a simple MLP
class MatchPredictor(nn.Module):
    def __init__(self, input_size, hidden_size=128):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x

input_size = X.shape[1]
torch_model = MatchPredictor(input_size).to(device)

criterion = nn.BCELoss()
optimizer = torch.optim.Adam(torch_model.parameters(), lr=0.001)

# ---------------------------
# Training loop
# ---------------------------
epochs = 20
for epoch in range(epochs):
    torch_model.train()
    total_loss = 0
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        preds = torch_model(xb).squeeze()
        loss = criterion(preds, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    
    # Validation
    torch_model.eval()
    with torch.no_grad():
        val_preds = torch_model(X_val_tensor.to(device)).squeeze()
        val_loss = criterion(val_preds, y_val_tensor.to(device)).item()
        val_acc = ((val_preds >= 0.5) == y_val_tensor.bool().to(device)).float().mean().item()
    
    print(f"Epoch {epoch+1}/{epochs} "
          f"Train Loss: {total_loss/len(train_loader):.4f} "
          f"Val Loss: {val_loss:.4f} Val Acc: {val_acc:.3f}")

# ---------------------------
# Save the trained model
# ---------------------------
torch.save(torch_model.state_dict(), "match_predictor.pt")
print("Model saved to match_predictor.pt")

# ---------------------------
# Reload for inference
# ---------------------------
loaded_model = MatchPredictor(input_size)
loaded_model.load_state_dict(torch.load("match_predictor.pt", map_location=device))
loaded_model.to(device)
loaded_model.eval()

# Example inference
with torch.no_grad():
    sample = torch.tensor(X[0], dtype=torch.float32).unsqueeze(0).to(device)
    prob = loaded_model(sample).item()
    print("Predicted prob team_0 wins:", prob)
#     js = fetch_match_data(name)
#     match_list = js['data']['matches']
#     for match in match_list:
#         print(match)
#         match_id = match['attributes']['id']
#         m_js = fetch_ind_match(match_id)
#         print(m_js)
        


   # https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/    ign/ProfChloroform?mode=competitive&season=7

   # https://api.tracker.gg/api/v2/marvel-rivals/standard/matches/    5517738_1756954559_1290271_11001_11

    


