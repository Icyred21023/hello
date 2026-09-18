import os, json, random
from itertools import combinations
import numpy as np
import tensorflow as tf
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"✅ TensorFlow detected {len(gpus)} GPU(s):")
    for gpu in gpus:
        print("   •", gpu)
else:
    print("❌ No GPU detected. Using CPU instead.")
from tensorflow import keras
from tensorflow.keras import layers
import helpers
# ============================================================
# Helpers (optional: adapt to your own path helper)
# ============================================================
def create_path(name, subdir="debug"):
    base = os.path.join(os.getcwd(), subdir) if subdir else os.getcwd()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, name)

# ============================================================
# 1) Data Loading
# ============================================================
def load_matches(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data):,} matches from {path}")
    return data

# ============================================================
# 2) Vocabulary Builder
# ============================================================
def build_vocab(matches):
    hero_set = set()
    for m in matches:
        for team in m["teams"]:
            for player in team["players"]:
                for hero in player["heroes"]:
                    hero_set.add(hero["name"].strip())
    hero2id = {h: i for i, h in enumerate(sorted(hero_set))}
    print(f"✅ Built hero vocab of size {len(hero2id)}")
    return hero2id

# ============================================================
# 3) Vectorization
# ============================================================
def encode_team(team, hero2id, num_heroes, k=8.0):
    """
    Builds a gated + normalized time-weighted hero vector for a team.

    ✅ Uses the same gating curve as team_hero_weights() for consistency.
    ✅ Each player's heroes are renormalized so their total time_used = 1.0.
    ✅ The team vector sums gated contributions from all players.
    """

    def gate_time_used(t, k=8.0):
        return 1.0 / (1.0 + np.exp(-k * (t - 0.5)))

    vec = np.zeros(num_heroes, dtype=np.float32)

    for player in team.get("players", []):
        raw_times = {}
        for hero in player.get("heroes", []):
            name = hero.get("name", "").strip()
            if not name or name not in hero2id:
                continue
            idx = hero2id[name]
            t = float(hero.get("time_used", 0.0))
            if t > 0:
                raw_times[idx] = raw_times.get(idx, 0.0) + t

        if raw_times:
            # Apply gating and renormalize per player
            gated = {hid: gate_time_used(v, k) for hid, v in raw_times.items()}
            total = sum(gated.values())
            if total > 0:
                gated = {hid: v / total for hid, v in gated.items()}

            # Add gated contributions to team vector
            for hid, v in gated.items():
                vec[hid] += v

    return vec


def team_hero_weights(team, hero2id, k=8.0):
    """
    Returns a dict {hero_id: gated_time_weight} for compact pair/trio loops.

    ✅ Applies a symmetric gating curve to reduce noise from low-time swaps.
       - Values near 0.5 stay similar.
       - Values <0.5 get reduced sharply (less impact).
       - Values >0.5 get boosted (more impact).

    ✅ After gating, re-normalizes all heroes for this player
       so total time_used across all heroes = 1.0.

    ✅ Then merges across team members, summing their gated times.
    """

    def gate_time_used(t, k=8.0):
        # Symmetric sigmoid gate centered at 0.5
        return 1.0 / (1.0 + np.exp(-k * (t - 0.5)))

    acc = {}

    for player in team["players"]:
        raw_times = {}
        for hero in player.get("heroes", []):
            name = hero.get("name", "").strip()
            if not name or name not in hero2id:
                continue
            idx = hero2id[name]
            t = float(hero.get("time_used", 0.0))
            if t > 0:
                raw_times[idx] = raw_times.get(idx, 0.0) + t

        # Apply gating + normalization per player
        if raw_times:
            gated = {hid: gate_time_used(v, k) for hid, v in raw_times.items()}
            total = sum(gated.values())
            if total > 0:
                gated = {hid: v / total for hid, v in gated.items()}

            # Merge into team-level accumulator
            for hid, v in gated.items():
                acc[hid] = acc.get(hid, 0.0) + v

    # prune zeros
    return {h: w for h, w in acc.items() if w > 0.0}


def export_hero_stats_json(hero2id, npz_path=None, out_name="hero_summary.json"):
    """
    Parse matchup_dataset_v3.npz and export per-hero statistics.

    Each hero entry contains:
      - winrate_1v1: avg 1v1 win ratio across all enemies
      - winrate_global: overall hero winrate (weighted by time played)
      - std_1v1: std deviation of hero's 1v1 rates
      - pair_synergy: avg within-team pair synergy
      - pair_vs_enemy: avg pair-vs-enemy advantage
      - 1v1_vs: dict of per-hero matchup winrates
      - id: hero numeric index
    """
    import os, json, numpy as np

    if npz_path is None:
        npz_path = helpers.create_path("matchup_dataset_v3.npz", "_MODEL_DATA")

    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"❌ No dataset found at {npz_path}")

    print(f"✅ Loading {npz_path} ...")
    data = np.load(npz_path)

    # --- Extract stored arrays ---
    rate_1v1 = data["rate_1v1"]
    pair_rate = data["pair_rate"]
    pair_vs_rate = data["pair_vs_rate"]
    hero_winrate_global = data["hero_winrate_global"]
    hero_1v1_full = data["hero_1v1_winrate_full"]

    H = rate_1v1.shape[0]
    id2hero = {v: k for k, v in hero2id.items()}
    hero_stats = {}

    for i in range(H):
        name = id2hero.get(i, f"hero_{i}")
        name = convert_key_to_name(name)

        # --- 1v1 stats ---
        row_avg = np.mean(rate_1v1[i, :])
        col_avg = np.mean(rate_1v1[:, i])
        global_wr = 0.5 * (row_avg + col_avg)
        std_1v1 = np.std(rate_1v1[i, :])

        # --- Pair synergy (avg of upper triangle pairs involving hero i)
        row_mask = np.triu_indices(H, k=1)
        pair_mask = (row_mask[0] == i) | (row_mask[1] == i)
        pair_values = pair_rate[row_mask][pair_mask]
        avg_pair = np.mean(pair_values) if pair_values.size > 0 else 0.5

        # --- Pair-vs-enemy synergy ---
        pv_values = pair_vs_rate[i, :, :].flatten()
        avg_pair_vs = np.mean(pv_values) if pv_values.size > 0 else 0.5

        # --- Full 1v1 matchup table for this hero ---
        one_v_one_vs = {}
        for j in range(H):
            if i == j:
                continue
            opp_name = convert_key_to_name(id2hero.get(j, f"hero_{j}"))
            one_v_one_vs[opp_name] = float(hero_1v1_full[i, j])

        hero_stats[name] = {
            "id": int(i),
            "winrate_1v1": float(row_avg),
            "winrate_global": float(hero_winrate_global[i]),
            "std_1v1": float(std_1v1),
            "pair_synergy": float(avg_pair),
            "pair_vs_enemy": float(avg_pair_vs),
            "1v1_vs": one_v_one_vs
        }

    # --- Save to JSON ---
    out_path = helpers.create_path(out_name, "_MODEL_DATA")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hero_stats, f, indent=2)
    print(f"✅ Exported hero stats to {out_path} ({len(hero_stats)} heroes)")

    return hero_stats

def compute_hero_global_winrate(matches, hero2id, alpha=1.0, beta=2.0):
    H = len(hero2id)
    hero_time_total = np.zeros(H, dtype=np.float64)  # total time played
    hero_time_won   = np.zeros(H, dtype=np.float64)  # time played on winning teams

    for m in matches:
        if len(m.get("teams", [])) != 2:
            continue
        A, B = m["teams"]
        for team in (A, B):
            wdict = team_hero_weights(team, hero2id)  # {hid: time_used_sum}
            if not wdict:
                continue
            # (optional) normalize team time to 6.0 total so matches are comparable
            team_sum = sum(wdict.values())
            if team_sum > 0:
                norm = 6.0 / team_sum
            else:
                norm = 1.0
            for hid, t in wdict.items():
                wt = t * norm
                hero_time_total[hid] += wt
                if team["bWon"]:
                    hero_time_won[hid] += wt

    # Laplace smoothing
    hero_winrate_global = (hero_time_won + alpha) / (hero_time_total + beta)
    return hero_winrate_global

def build_dataset_with_matchups(matches, hero2id, val_ratio=0.0,
                                laplace_alpha=1.0, laplace_beta=2.0):
    """
    Build augmented feature matrix with hero-vs-hero, pair, trio, and
    new pair-vs-enemy synergy advantages. Also records hero ID lists
    (team0_ids and team1_ids) for hybrid model training.

    ✅ NEW:
      • Adds per-match sample weights based on number of hero swaps.
        (fewer swaps = higher confidence weight)
      • Saves weights in dataset (.npz) for use in model.fit()
    """

    datasetpath = helpers.create_path("matchup_dataset_v3.npz", "_MODEL_DATA")
    if os.path.exists(datasetpath):
        data = np.load(datasetpath)
        X, y = data["X"], data["y"]
        if val_ratio and val_ratio > 0.0:
            idx = np.arange(len(X))
            np.random.shuffle(idx)
            split = int(len(X) * (1 - val_ratio))
            train = (X[idx[:split]], y[idx[:split]])
            val   = (X[idx[split:]], y[idx[split:]])
        else:
            train, val = (X, y), None
        return train, val

    H = len(hero2id)
    eps = 1e-8

    # ---------- Storage ----------
    meet_1v1 = np.zeros((H, H), dtype=np.float64)
    win_1v1  = np.zeros((H, H), dtype=np.float64)
    lose_1v1 = np.zeros((H, H), dtype=np.float64)
    meet_pair = np.zeros((H, H), dtype=np.float64)
    win_pair  = np.zeros((H, H), dtype=np.float64)
    meet_pair_vs = np.zeros((H, H, H), dtype=np.float64)
    win_pair_vs  = np.zeros((H, H, H), dtype=np.float64)
    meet_trio, win_trio = {}, {}

    hero_time_total = np.zeros(H, dtype=np.float64)
    hero_time_won   = np.zeros(H, dtype=np.float64)

    def add_trio_count(bucket, key, v):
        bucket[key] = bucket.get(key, 0.0) + v

    # ---------- First pass ----------
    for m in matches:
        if len(m.get("teams", [])) != 2:
            continue
        A, B = m["teams"]
        winner = A if A["bWon"] else B
        loser  = B if A["bWon"] else A

        w_dict = team_hero_weights(winner, hero2id)
        l_dict = team_hero_weights(loser,  hero2id)
        if not w_dict or not l_dict:
            continue

        # --- Global hero time winrates ---
        for team in (A, B):
            hdict = team_hero_weights(team, hero2id)
            if not hdict:
                continue
            team_sum = sum(hdict.values())
            norm = 6.0 / team_sum if team_sum > 0 else 1.0
            for hid, t in hdict.items():
                wt = t * norm
                hero_time_total[hid] += wt
                if team["bWon"]:
                    hero_time_won[hid] += wt

        # --- Full 1v1 tracking (directional win/loss) ---
        for hi, wi in w_dict.items():
            for hj, wj in l_dict.items():
                wprod = wi * wj
                win_1v1[hi, hj]  += wprod  # hi beat hj
                lose_1v1[hj, hi] += wprod  # hj lost to hi
                meet_1v1[hi, hj] += wprod
                meet_1v1[hj, hi] += wprod

        # --- Pair synergy ---
        def accum_pairs(hdict, won):
            hs = sorted(hdict.items())
            for (i, wi), (j, wj) in combinations(hs, 2):
                v = wi * wj
                meet_pair[i, j] += v
                if won:
                    win_pair[i, j] += v
        accum_pairs(team_hero_weights(A, hero2id), A["bWon"])
        accum_pairs(team_hero_weights(B, hero2id), B["bWon"])

        # --- Pair vs enemy ---
        for (i, wi), (j, wj) in combinations(w_dict.items(), 2):
            for k, wk in l_dict.items():
                v = wi * wj * wk
                win_pair_vs[i, j, k]  += v
                meet_pair_vs[i, j, k] += v
                meet_pair_vs[j, i, k] += v
        for (i, wi), (j, wj) in combinations(l_dict.items(), 2):
            for k, wk in w_dict.items():
                v = wi * wj * wk
                meet_pair_vs[i, j, k] += v
                meet_pair_vs[j, i, k] += v

        # --- Trio synergy ---
        def accum_trios(hdict, won):
            hs = sorted(hdict.items())
            for (i, wi), (j, wj), (k, wk) in combinations(hs, 3):
                v = wi * wj * wk
                key = (i, j, k)
                add_trio_count(meet_trio, key, v)
                if won:
                    add_trio_count(win_trio, key, v)
        accum_trios(team_hero_weights(A, hero2id), A["bWon"])
        accum_trios(team_hero_weights(B, hero2id), B["bWon"])

    # ---------- Convert to rates ----------
    rate_1v1 = (win_1v1 + laplace_alpha) / (meet_1v1 + laplace_beta)
    pair_rate = np.zeros_like(meet_pair)
    mask = meet_pair > 0
    pair_rate[mask] = (win_pair[mask] + laplace_alpha) / (meet_pair[mask] + laplace_beta)
    pair_vs_rate = (win_pair_vs + laplace_alpha) / (meet_pair_vs + laplace_beta)
    hero_winrate_global = (hero_time_won + laplace_alpha) / (hero_time_total + laplace_beta)
    hero_1v1_winrate_full = (win_1v1 + laplace_alpha) / (win_1v1 + lose_1v1 + laplace_beta)

    def trio_rate(i, j, k):
        key = tuple(sorted((i, j, k)))
        m = meet_trio.get(key, 0.0)
        w = win_trio.get(key, 0.0)
        return (w + laplace_alpha) / (m + laplace_beta)

    # ---------- Second pass ----------
    X_rows, y = [], []
    team0_ids, team1_ids = [], []
    X_rows, y = [], []
    team0_ids, team1_ids = [], []

    for m in matches:
        if len(m.get("teams", [])) != 2:
            continue
        t0, t1 = m["teams"]
        t0_vec = encode_team(t0, hero2id, H)
        t1_vec = encode_team(t1, hero2id, H)
        label = 1.0 if t0["bWon"] else 0.0

        if random.random() < 0.5:
            t0_vec, t1_vec = t1_vec, t0_vec
            label = 1.0 - label
            t0_local, t1_local = t1, t0
        else:
            t0_local, t1_local = t0, t1

        diff = np.abs(t0_vec - t1_vec)
        prod = t0_vec * t1_vec
        base_feat = np.concatenate([t0_vec, t1_vec, diff, prod], axis=0)

        A_dict = team_hero_weights(t0_local, hero2id)
        B_dict = team_hero_weights(t1_local, hero2id)

        # --- 1v1 advantage ---
        if A_dict and B_dict:
            num_fw = den_fw = num_bw = den_bw = 0.0
            for i, wi in A_dict.items():
                for j, wj in B_dict.items():
                    wprod = wi * wj
                    num_fw += rate_1v1[i, j] * wprod
                    den_fw += wprod
                    num_bw += rate_1v1[j, i] * wprod
                    den_bw += wprod
            hvh_adv = (num_fw / (den_fw + eps)) - (num_bw / (den_bw + eps))
        else:
            hvh_adv = 0.0

        # --- Pair synergy within team ---
        def avg_pair_rate(hdict):
            hs = list(hdict.items())
            if len(hs) < 2: return 0.5
            num = den = 0.0
            for (i, wi), (j, wj) in combinations(hs, 2):
                i0, j0 = (i, j) if i < j else (j, i)
                num += pair_rate[i0, j0] * (wi * wj)
                den += (wi * wj)
            return num / (den + eps)
        pair_adv = avg_pair_rate(A_dict) - avg_pair_rate(B_dict)

        # --- Trio synergy ---
        def avg_trio_rate(hdict):
            hs = list(hdict.items())
            if len(hs) < 3: return 0.5
            num = den = 0.0
            for (i, wi), (j, wj), (k, wk) in combinations(hs, 3):
                num += trio_rate(i, j, k) * (wi * wj * wk)
                den += (wi * wj * wk)
            return num / (den + eps)
        trio_adv = avg_trio_rate(A_dict) - avg_trio_rate(B_dict)

        # --- Pair-vs-enemy advantage ---
        def pair_vs_enemy_adv(A_dict, B_dict):
            hs = list(A_dict.items())
            es = list(B_dict.items())
            if len(hs) < 2 or not es:
                return 0.0
            num = den = 0.0
            for (i, wi), (j, wj) in combinations(hs, 2):
                for (k, wk) in es:
                    v = wi * wj * wk
                    num += (pair_vs_rate[i, j, k] - 0.5) * v
                    den += v
            return num / (den + eps)
        pair_vs_adv = pair_vs_enemy_adv(A_dict, B_dict) - pair_vs_enemy_adv(B_dict, A_dict)

        aug_feat = np.array([hvh_adv, pair_adv, trio_adv, pair_vs_adv], dtype=np.float32)
        features = np.concatenate([base_feat, aug_feat], axis=0)

        def extract_team_ids(team):
            ids = [hero2id[h["heroes"][0]["name"]] for h in team["players"]
                   if "heroes" in h and h["heroes"]]
            ids = (ids + [0]*6)[:6]
            return np.array(ids, dtype=np.int32)

        team0_ids.append(extract_team_ids(t0_local))
        team1_ids.append(extract_team_ids(t1_local))
        X_rows.append(features.astype(np.float32))
        y.append(label)

    X = np.stack(X_rows, axis=0)
    y = np.array(y, dtype=np.float32)
    team0_ids = np.stack(team0_ids, axis=0)
    team1_ids = np.stack(team1_ids, axis=0)

    print(f"✅ Vectorized dataset (v4): {X.shape[0]} samples, {X.shape[1]} features")

    # ---------- Save ----------
    np.savez(
        datasetpath,
        X=X,
        y=y,
        team0_ids=team0_ids,
        team1_ids=team1_ids,
        rate_1v1=rate_1v1,
        pair_rate=pair_rate,
        pair_vs_rate=pair_vs_rate,
        hero_winrate_global=hero_winrate_global,
        hero_1v1_winrate_full=hero_1v1_winrate_full
    )
    print(f"✅ Cached dataset saved to {datasetpath}")


    # ---------- Split ----------
    if val_ratio and val_ratio > 0.0:
        idx = np.arange(len(X))
        np.random.shuffle(idx)
        split = int(len(X) * (1 - val_ratio))
        train = (X[idx[:split]], y[idx[:split]])
        val   = (X[idx[split:]], y[idx[split:]])
    else:
        train, val = (X, y), None

    return train, val



import numpy as np

def match_model_input(model, features: np.ndarray) -> np.ndarray:
    """
    Pads or trims the numeric feature vector so its length matches
    the hybrid model's numeric_features input shape.
    """
    # Find numeric input tensor
    for inp in model.inputs:
        if inp.name.startswith("numeric_features"):
            expected = inp.shape[-1]
            break
    else:
        expected = model.input_shape[0][-1]

    current = features.shape[-1]
    if current < expected:
        pad = np.zeros((expected - current,), dtype=np.float32)
        features = np.concatenate([features, pad])
    elif current > expected:
        features = features[:expected]
    return features


def score_hero_vs_enemy(model, hero_name, enemy_vec, hero2id):
    H = len(hero2id)
    team_vec = np.zeros(H, dtype=np.float32)
    team_vec[hero2id[hero_name]] = 1.0

    diff = np.abs(team_vec - enemy_vec)
    prod = team_vec * enemy_vec
    feat = np.concatenate([team_vec, enemy_vec, diff, prod])
    feat = match_model_input(model, feat)        # ✅ ensure correct length
    feat = feat[None, :]                         # add batch dimension
    return float(model.predict(feat, verbose=0)[0, 0])


import random

def build_counter_team(model, enemy_team, hero2id, herokeys=None,
                       num_candidates=200000, team_size=6, tank=2, heal=2, dps=2):
    """
    Hybrid-aware Monte Carlo counter search.
    Uses hybrid model inputs (numeric + team IDs) so synergy priors are active.
    """
    import numpy as np, random, time

    all_heroes = list(hero2id.keys())
    keylist = herokeys['data']['items']
    H = len(hero2id)

    # --- Encode enemy once ---
    enemy_vec = np.zeros(H, dtype=np.float32)
    for player in enemy_team["players"]:
        for hero in player["heroes"]:
            idx = hero2id.get(hero["name"])
            if idx is not None:
                enemy_vec[idx] += float(hero.get("time_used", 1.0))

    # --- Role mapping ---
    role_map = {h["key"]: h["roleKey"] for h in keylist if "key" in h and "roleKey" in h}

    def random_team():
        """Sample a valid team under role limits."""
        duelist = vanguard = strategist = 0
        selected = []
        heroes = random.sample(keylist, len(keylist))
        for entry in heroes:
            hid, role = entry["key"], entry["roleKey"]
            if hid not in all_heroes or hid in selected or hid == "1033":
                continue
            if role == "vanguard" and vanguard >= tank:
                continue
            if role == "strategist" and strategist >= heal:
                continue
            if role == "duelist" and duelist >= dps:
                continue

            selected.append(hid)
            if role == "vanguard": vanguard += 1
            elif role == "strategist": strategist += 1
            elif role == "duelist": duelist += 1
            if len(selected) >= team_size:
                break
        return selected if len(selected) == team_size else None

    # --- Generate candidate teams ---
    teams = []
    while len(teams) < num_candidates:
        t = random_team()
        if t:
            teams.append(t)
    print(f"✅ Generated {len(teams):,} candidate teams")

    # --- Prepare model inputs ---
    feats_fwd, feats_bwd = [], []
    team0_ids_list, team1_ids_list = [], []
    team0_ids_list_b, team1_ids_list_b = [], []

    for t in teams:
        # build team vector
        team_vec = np.zeros(H, dtype=np.float32)
        for hid in t:
            if hid in hero2id:
                team_vec[hero2id[hid]] = 1.0

        diff = np.abs(team_vec - enemy_vec)
        prod = team_vec * enemy_vec
        aug  = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)

        fwd = np.concatenate([team_vec, enemy_vec, diff, prod, aug])
        bwd = np.concatenate([enemy_vec, team_vec, diff, prod, aug])

        feats_fwd.append(match_model_input(model, fwd))
        feats_bwd.append(match_model_input(model, bwd))

        # Build team ID arrays
        def team_ids_from_keys(keys):
            ids = [hero2id[k] for k in keys if k in hero2id]
            ids = (ids + [0]*6)[:6]
            return np.array(ids, dtype=np.int32)

        team0_ids_list.append(team_ids_from_keys(t))
        team1_ids_list.append(team_ids_from_keys([h["name"] for p in enemy_team["players"] for h in p["heroes"]]))
        team0_ids_list_b.append(team1_ids_list[-1])
        team1_ids_list_b.append(team0_ids_list[-1])
    def adjust_confidence(conf, temperature=2.0, contrast=1.3):
        """
        Apply temperature scaling + normalization + contrast sharpening.
        """
        # 1️⃣ Clip to avoid infinities in logit
        conf = np.clip(conf, 1e-12, 1 - 1e-12)

        # 2️⃣ Temperature scaling (soften extreme 0/1)
        logit = np.log(conf / (1 - conf))
        scaled = 1 / (1 + np.exp(-logit / temperature))

        # 3️⃣ Normalize to 0–1 again
        scaled = np.clip(scaled, 1e-12, 1 - 1e-12)
        scaled = (scaled - scaled.min()) / (scaled.max() - scaled.min() + 1e-9)

        # 4️⃣ Apply contrast curve
        scaled = scaled ** contrast

        return scaled
    # Stack arrays
    feats_fwd = np.asarray(feats_fwd, dtype=np.float32)
    feats_bwd = np.asarray(feats_bwd, dtype=np.float32)
    team0_ids_arr = np.asarray(team0_ids_list, dtype=np.int32)
    team1_ids_arr = np.asarray(team1_ids_list, dtype=np.int32)
    team0_ids_b = np.asarray(team0_ids_list_b, dtype=np.int32)
    team1_ids_b = np.asarray(team1_ids_list_b, dtype=np.int32)

    # --- Predict in batches ---
    start = time.time()
    pf = model.predict([feats_fwd, team0_ids_arr, team1_ids_arr], verbose=0).reshape(-1)
    pb = model.predict([feats_bwd, team0_ids_b, team1_ids_b], verbose=0).reshape(-1)

    confs = 0.5 * (pf + (1.0 - pb))
    confs = adjust_confidence(confs, temperature=2, contrast=1.8)

    print(f"✅ Evaluated {len(confs):,} candidate teams in {time.time()-start:.2f}s")
    top50 = []
    for i, conf in enumerate(confs):
        if conf > 0.9:
            top50.append((teams[i], conf))

        # --- pick best team ---
    best_idx = int(np.argmax(confs))
    best_team, best_conf = teams[best_idx], float(confs[best_idx])
    print(f"🏆 Best Counter Team (conf={best_conf:.3f}): {best_team}")
    return best_team, best_conf, top50
# ============================================================
# 5) Model
# ============================================================
def build_model(input_dim):
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(512, activation="relu"),
        layers.Dropout(0.30),
        layers.Dense(256, activation="relu"),
        layers.Dropout(0.30),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.30),
        layers.Dense(1, activation="sigmoid")
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=5e-4),
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )
    return model

from tensorflow.keras import Model
def make_hybrid_model(H, feature_dim,
                      rate_1v1, pair_rate, pair_vs_rate,
                      dense_units=(512, 256), dropout=0.25):
    """
    Final hybrid model integrating:
      • 1v1 matchup priors
      • pair synergy priors
      • pair-vs-enemy priors
    """

    # === Inputs ===
    x_in = layers.Input(shape=(feature_dim,), name="numeric_features")
    team0_in = layers.Input(shape=(6,), dtype=tf.int32, name="team0_ids")
    team1_in = layers.Input(shape=(6,), dtype=tf.int32, name="team1_ids")

    # === Trainable matchup embeddings ===
    rate_1v1_embed = tf.Variable(rate_1v1, dtype=tf.float32, trainable=True, name="rate_1v1_embed")
    pair_rate_embed = tf.Variable(pair_rate, dtype=tf.float32, trainable=True, name="pair_rate_embed")
    pair_vs_rate_embed = tf.Variable(pair_vs_rate, dtype=tf.float32, trainable=True, name="pair_vs_rate_embed")

    # --- 1v1 matchup average (batch-safe) ---
    def lookup_1v1(team0_ids, team1_ids):
        # gather hero rows from rate_1v1
        sub = tf.gather(rate_1v1_embed, team0_ids)          # [batch,6,H]
        sub = tf.gather(sub, team1_ids, batch_dims=1)       # [batch,6,6]
        return tf.reduce_mean(sub, axis=[1,2], keepdims=True)  # [batch,1,1]

    hvh_prior = layers.Lambda(lambda x: lookup_1v1(x[0], x[1]))([team0_in, team1_in])

    # --- average pair synergy within each team (batch-safe) ---
    def avg_pair_synergy(ids):
        sub = tf.gather(pair_rate_embed, ids)             # [batch,6,H]
        sub = tf.gather(sub, ids, batch_dims=1)           # [batch,6,6]
        return tf.reduce_mean(sub, axis=[1,2], keepdims=True)

    pair0 = layers.Lambda(lambda ids: avg_pair_synergy(ids))(team0_in)
    pair1 = layers.Lambda(lambda ids: avg_pair_synergy(ids))(team1_in)
    pair_diff = layers.Subtract()([pair0, pair1])  # [batch,1,1]

    # --- pair-vs-enemy synergy (simplified) ---
    def pair_vs_enemy(team0_ids, team1_ids):
        # shape: [batch,6,6,6]
        vals = tf.gather(pair_vs_rate_embed, team0_ids)              # [batch,6,H,H]
        vals = tf.gather(vals, team0_ids, batch_dims=1)              # [batch,6,6,H]
        vals = tf.gather(vals, team1_ids, batch_dims=1)              # [batch,6,6,6]
        return tf.reduce_mean(vals, axis=[1,2,3], keepdims=True)     # [batch,1,1]

    pair_vs_adv = layers.Lambda(lambda x: pair_vs_enemy(x[0], x[1]))([team0_in, team1_in])

    # --- Combine all priors ---
    # Ensure all tensors are rank-2 before concatenation
    hvh_flat = layers.Flatten()(hvh_prior)
    pair_diff_flat = layers.Flatten()(pair_diff)
    pair_vs_flat = layers.Flatten()(pair_vs_adv)

    matchup_feat = layers.Concatenate(name="matchup_priors")([hvh_flat, pair_diff_flat, pair_vs_flat])


    # --- Merge with numeric features ---
    concat = layers.Concatenate(name="merged_features")([x_in, matchup_feat])

    # --- Dense prediction head ---
    h = concat
    for i, u in enumerate(dense_units):
        h = layers.Dense(
            u,
            activation="relu",
            kernel_regularizer=tf.keras.regularizers.l2(1e-5),  # ✅ L2 regularization
            name=f"dense_{i+1}"
        )(h)
        h = layers.Dropout(dropout)(h)

    # --- Softer sigmoid output (less overconfidence) ---
    out = layers.Dense(
        1,
        activation=lambda x: tf.nn.sigmoid(x / 2.0),  # ✅ Temperature-scaling sigmoid
        name="win_prob"
    )(h)

    # === Compile ===
    loss = tf.keras.losses.BinaryCrossentropy(label_smoothing=0.02)  # ✅ Label smoothing
    model = Model(inputs=[x_in, team0_in, team1_in], outputs=out)
    model.compile(optimizer="adam", loss=loss, metrics=["accuracy"])
    model.summary()
    return model



    # h = concat
    # for i, u in enumerate(dense_units):
    #     h = layers.Dense(u, activation="relu", name=f"dense_{i+1}")(h)
    #     h = layers.Dropout(dropout)(h)
    # out = layers.Dense(1, activation="sigmoid", name="win_prob")(h)

    # model = Model(inputs=[x_in, team0_in, team1_in], outputs=out)
    # model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    # model.summary()
    # return model
# ============================================================
# 6) Training
# ============================================================
def train_model(train_data, val_data, out_dir, epochs=400, batch_size=512, patience=15):
    os.makedirs(out_dir, exist_ok=True)
    ckpt_path = os.path.join(out_dir, "_NewMatchModel_tf.keras")

    X_train, y_train = train_data
    model = build_model(X_train.shape[1])

    callbacks = [keras.callbacks.EarlyStopping(
    monitor="accuracy",  # ← change this line
    patience=patience,
    restore_best_weights=True
)]
    if val_data is not None:
        callbacks.append(
            keras.callbacks.ModelCheckpoint(
                ckpt_path, monitor="val_accuracy", save_best_only=True, verbose=1
            )
        )
        print(f"🧠 Training on {len(X_train):,} samples, validating on {len(val_data[0]):,}")
        hist = model.fit(
            X_train, y_train,
            validation_data=val_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=2
        )
        best_acc = max(hist.history["val_accuracy"])
    else:
        callbacks.append(
            keras.callbacks.ModelCheckpoint(
                ckpt_path, monitor="accuracy", save_best_only=True, verbose=1
            )
        )
        print(f"🧠 Training on {len(X_train):,} samples (no validation split).")
        hist = model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=2
        )
        best_acc = max(hist.history["accuracy"])

    print(f"✅ Training complete. Best Acc: {best_acc:.3f}")
    return ckpt_path, model

# ============================================================
# 7) Inference Utilities
# ============================================================
def load_model_tf(path):
    model = keras.models.load_model(path)
    print(f"✅ Loaded model from {path}")
    return model

def predict_match(model, hero2id, match):
    """
    Symmetry-averaged prediction for the hybrid model.
    Feeds numeric features + team hero IDs into the model.
    """
    H = len(hero2id)
    t0, t1 = match["teams"]

    # --- build numeric features ---
    t0_vec = encode_team(t0, hero2id, H)
    t1_vec = encode_team(t1, hero2id, H)
    diff = np.abs(t0_vec - t1_vec)
    prod = t0_vec * t1_vec
    # aug should have 4 scalars (since dataset used 4 augmented features)
    aug = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)

    fwd_features = np.concatenate([t0_vec, t1_vec, diff, prod, aug])[None, :]
    bwd_features = np.concatenate([t1_vec, t0_vec, diff, prod, aug])[None, :]

    # --- build team id arrays (pad to 6 heroes) ---
    def extract_team_ids(team):
        ids = [hero2id[h["heroes"][0]["name"]] for h in team["players"]
               if "heroes" in h and h["heroes"]]
        ids = (ids + [0]*6)[:6]
        return np.array(ids, dtype=np.int32)[None, :]  # add batch dim

    t0_ids = extract_team_ids(t0)
    t1_ids = extract_team_ids(t1)

    # --- forward and backward prediction (symmetry) ---
    p_fwd = model.predict([fwd_features, t0_ids, t1_ids], verbose=0)[0, 0]
    p_bwd = 1.0 - model.predict([bwd_features, t1_ids, t0_ids], verbose=0)[0, 0]

    prob = 0.5 * (p_fwd + p_bwd)
    winner = "team_0" if prob >= 0.5 else "team_1"
    conf = prob if winner == "team_0" else 1 - prob
    return winner, float(conf)

# ============================================================
# 8) Main
# ============================================================
def convert_to_match(best,ene):
    team0 = {'team_id':0, 'bWon': True, 'players': []}
    team1 = {'team_id':1, 'bWon': False, 'players': ene['players']}
    for name in best:
        
        da = {'heroes':[{'name': name, 'time_used': 1}]}
        team0['players'].append(da)
    m = {'match_id': '1', 'teams': []}
    m['teams'].append(team0)
    m['teams'].append(team1)
    return m
        
import numpy as np
from tqdm import tqdm

def probe_counters_for_hero(model, hero_name, hero2id):
    """
    Probes every hero in hero2id against a single target hero,
    returns sorted list of (hero, predicted_win_confidence)
    meaning: probability that this hero beats the target hero 1v1.
    """
    H = len(hero2id)
    # --- Build enemy vector with just the target hero ---
    enemy_vec = np.zeros(H, dtype=np.float32)
    target_idx = hero2id.get(hero_name)
    if target_idx is None:
        raise ValueError(f"Hero '{hero_name}' not in vocab")
    enemy_vec[target_idx] = 1.0

    results = []
    for candidate in tqdm(hero2id.keys(), desc=f"Probing vs {hero_name}"):
        if candidate == hero_name:
            continue
        score = score_hero_vs_enemy(model, candidate, enemy_vec, hero2id)
        results.append((candidate, score))

    # Sort descending: higher = better chance to win vs target
    results.sort(key=lambda x: x[1], reverse=True)
    return results

# Example usage:

        

def build_targetteam_list(names):
    players = []
    pa = helpers.create_path("hero_data_keys.json")
    hero_map = helpers.load_json(pa)

    for name in names:
        name = name.lower()
        for key in hero_map['data']['items']:
            hero_name = key['name'].lower()
            hero_key = key['key']
            if name == hero_name:
                players.append({"heroes": [{"name": hero_key, "time_used": 1.0}]})
                break
    print(f"✅Built target team.\n\n{players}")
    return {"players": players}, hero_map

def convert_key_to_name(keys):
    pa = helpers.create_path("hero_data_keys.json")
    hero_map = helpers.load_json(pa)
    
    if isinstance(keys, list):
        id_to_name = {key['key']: (key['name'].lower()) for key in hero_map['data']['items']}
        names = [id_to_name.get(k, k) for k in keys]
        return names
    elif isinstance(keys, str):
        id_to_name = {key['key']: (key['name'].lower()) for key in hero_map['data']['items']}
        return id_to_name.get(keys, keys)
    
def convert_name_to_key(n):
    pa = helpers.create_path("hero_data_keys.json")
    hero_map = helpers.load_json(pa)
    items = hero_map["data"]["items"]
    n = n.lower()
    # find matching dict (case-insensitive)
    match = next((h for h in items if h["name"].lower() == n), None)
    return match["key"] if match else None


def convert_counters(ac):
    ks = []
    c2 = []
    for h, s in ac:
        ks.append(h)
    ns = convert_key_to_name(ks)
    for i, item in enumerate(ac):
        h, s = item
        if s > 0.56:
            name = ns[i]
            c2.append((name, s))
        else:
            break
    if not c2:
        return False
    else:
        return c2
    
def convert_match_playerkeys_to_names(ma):
    pa = helpers.create_path("hero_data_keys.json")
    hero_map = helpers.load_json(pa)
    hero_items = hero_map['data']['items']
    key_to_name = {h["key"]: h["name"] for h in hero_items if "key" in h and "name" in h}
    team0 = ma['teams'][0]['players']
    team1 = ma['teams'][1]['players']
    team0_names = list({
        h["name"]
        for p in team0 if "heroes" in p
        for h in p["heroes"] if "name" in h
        })

    team1_names = list({
        h["name"]
        for p in team1 if "heroes" in p
        for h in p["heroes"] if "name" in h
        })

    team0_names = [key_to_name.get(n, n) for n in team0_names]
    team1_names = [key_to_name.get(n, n) for n in team1_names]

    return team0_names, team1_names

if __name__ == "__main__":
    
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RESET = "\033[0m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    # Path to your JSON
    bTrain = False
    bPredict = False
    bFindTeam = True
    bBuild = False
    DATA_PATH = helpers.create_path("_matches_restructured.json", "_MODEL_DATA")
    matches = load_matches(DATA_PATH)
    hero2id = build_vocab(matches)
    
    if bBuild:
        print("=== Building dataset with matchup features ===")
        build_dataset_with_matchups(
            matches, hero2id, val_ratio=0.0
        )
        #print("✅ Dataset built successfully.")
        export_hero_stats_json(hero2id )

    if bFindTeam:
        
        enemy_team = ["Luna Snow", "Namor", "Magneto", "Peni Parker", "Winter Soldier", "Cloak & Dagger"]
        enemy_team = ["Doctor Strange", "Bruce Banner", "Iron Man", "The Punisher", "Invisible Woman", "Cloak & Dagger"]
        target_team, heromap= build_targetteam_list(enemy_team)
        
        
    out_dir = helpers.create_path("_MODEL_DATA", "")
    ckpt_path = os.path.join(out_dir, "hybrid_model.keras")
    if not bTrain:
        print("✅ Loading hybrid model from checkpoint ...")
        data_path = helpers.create_path("matchup_dataset_v3.npz", "_MODEL_DATA")
        if not os.path.exists(data_path):
            raise FileNotFoundError("❌ matchup_dataset_v3.npz not found — run dataset builder first.")
        data = np.load(data_path)
        rate_1v1 = data["rate_1v1"]
        pair_rate = data["pair_rate"]
        pair_vs_rate = data["pair_vs_rate"]

        H = len(hero2id)
        feature_dim = 168  # or infer dynamically if you want (see below)

        # rebuild architecture
        model = make_hybrid_model(H, feature_dim, rate_1v1, pair_rate, pair_vs_rate)

        # now load weights (best or final)
        ckpt_path = os.path.join(out_dir, "hybrid_model_best.keras")
        if not os.path.exists(ckpt_path):
            ckpt_path = os.path.join(out_dir, "hybrid_model.keras")
        model.load_weights(ckpt_path)
        print(f"✅ Model weights loaded from {ckpt_path}")
    

    # Build dataset w/ live matchup features (set val_ratio=0.0 to train on ALL)
    if bTrain:
        ############ HYBRID MODEL TRAINING ############
        print("=== Building hybrid model training dataset ===")

        # === Build dataset ===
        (X_train, y_train), val_data = build_dataset_with_matchups(
            matches, hero2id, val_ratio=0.0
        )

        # === Export per-hero stats (optional diagnostic) ===
        export_hero_stats_json(hero2id)

        # === Load dataset tensors ===
        data_path = helpers.create_path("matchup_dataset_v3.npz", "_MODEL_DATA")
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"❌ Matchup dataset not found at {data_path}. Run dataset builder first.")

        print(f"✅ Loading matchup dataset from {data_path}")
        data = np.load(data_path)

        team0_ids = data["team0_ids"]
        team1_ids = data["team1_ids"]
        rate_1v1 = data["rate_1v1"]
        pair_rate = data["pair_rate"]
        pair_vs_rate = data["pair_vs_rate"]
        sample_weights = data.get("sample_weights", None)  # ✅ Load weights safely

        # === Build hybrid model ===
        H = len(hero2id)
        feature_dim = X_train.shape[1]

        model = make_hybrid_model(
            H,
            feature_dim,
            rate_1v1,
            pair_rate,
            pair_vs_rate
        )

        # === Training setup ===
        from tensorflow.keras.callbacks import ModelCheckpoint

        out_dir = helpers.create_path("_MODEL_DATA", "")
        best_ckpt_path = os.path.join(out_dir, "hybrid_model_best.keras")

        checkpoint_cb = ModelCheckpoint(
            filepath=best_ckpt_path,
            monitor="accuracy",
            mode="max",
            save_best_only=True,
            verbose=1
        )

        lr_schedule = keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.8,
            patience=5,
            verbose=1,
            min_lr=1e-6
        )

        # === Begin training ===
        print("✅ Starting hybrid training ...")

        fit_kwargs = dict(
            x=[X_train, team0_ids, team1_ids],
            y=y_train,
            epochs=300,
            batch_size=512,
            validation_split=0.05,
            callbacks=[checkpoint_cb, lr_schedule],
            verbose=1
        )
        print("✅ Using standard (unweighted) training.")


        history = model.fit(**fit_kwargs)

        # === Save final epoch ===
        ckpt_path = os.path.join(out_dir, "hybrid_model.keras")
        model.save(ckpt_path)
        print(f"✅ Hybrid model saved to {ckpt_path}")
        print(f"✅ Best validation model saved to {best_ckpt_path}")

            


    if bPredict:
    # Quick smoke test on a few samples
        correct = total = 0
        import time
        for i, sample in enumerate(matches[:50000]):
            w, c = predict_match(model, hero2id, sample)
            muid = sample.get("match_id", "N/A")
            
            #team0_name, team1_name = convert_match_playerkeys_to_names(sample)
            true_w = "team_0" if sample["teams"][0]["bWon"] else "team_1"
            #t0color = GREEN if sample["teams"][0]["bWon"] else RED
            #t1color = GREEN if sample["teams"][1]["bWon"] else RED
            ok = (w == true_w)
            correct += int(ok); total += 1

            print(
                    f"{'✅' if ok else '❌'} {i+1:03d}:  {BOLD}{YELLOW}{muid}{RESET} - ",
                    f"Pred={w} ({c:.3f}) | Act-{true_w} | Acc={correct/total:.3f} | ",
                    #f"Team 0: {t0color}{team0_name}{RESET} | Team 1: {t1color}{team1_name}{RESET}",
                    #end="\r",
                    #flush=False
                )
            #time.sleep(0.001)
    if bFindTeam:
        from collections import Counter
        co = enemy_team
        enemy_team = target_team
        all_heroes = list(hero2id.keys())
        best_team, conf, top = build_counter_team(model, enemy_team,hero2id, herokeys=heromap)
        idx = 0
        correct = 0
        total = 0
        hero_freq = Counter()
        for (best_team, conf) in top:
            idx += 1
            
            best_names = convert_key_to_name(best_team)
            hero_freq.update(best_names)
            matchh = convert_to_match(best_team,enemy_team)
            w, c = predict_match(model, hero2id, matchh)
            true_w = "team_0" if matchh["teams"][0]["bWon"] else "team_1"
            ok = (w == true_w)
            correct += int(ok); total += 1
            print(f"{idx}: Counter Team: {BLUE}{best_names}{RESET} | Score={YELLOW}{conf:.3f}{RESET} | {'✅' if ok else '❌'} Pred={w} ({c:.3f}) | {RED}{co}{RESET} | Acc={correct/total:.3f}")
        print("🔥 Top hero appearances among >0.9 confidence teams:")
        for hero, count in hero_freq.most_common():
            print(f"{hero:20s}  {count}")

        # matchh = convert_to_match(best_team,enemy_team)
        # p = helpers.create_path('match_convert.json','_MODEL_DATA')
        # helpers.save_json(p, matchh)
        # correct = 0
        # total = 0
        # w, c = predict_match(model, hero2id, matchh)
        # true_w = "team_0" if matchh["teams"][0]["bWon"] else "team_1"
        # ok = (w == true_w)
        # correct += int(ok); total += 1
        # print(f"{'✅' if ok else '❌'}: Pred={w} ({c:.3f}) | Real={true_w} | Acc={correct/total:.3f}")
        # best_names = convert_key_to_name(best_team)
        # print("✅ Recommended Counter Team:", best_names)
            