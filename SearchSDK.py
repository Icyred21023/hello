import os

# === 🔧 CONFIGURATION ===
# Put the directory you want to search here:
SEARCH_DIR = r"C:\Users\Corey\Desktop\py\5.3.2-2327098+++depot_marvel+S4.0_release-Marvel\CppSDK\SDK"  # example path on Android

# Words or phrases to search for (case-insensitive)
SEARCH_TERMS = ["OnRep_KillScore"]

# =========================

def search_files(search_dir, search_terms):
    matched_files = []
    search_terms = [term.lower() for term in search_terms]

    for root, _, files in os.walk(search_dir):
        for fname in files:
            # only consider text-like files
            if not fname.lower().endswith((".txt", ".cpp", ".hpp", ".h", ".ini", ".json", ".uasset", ".cs")):
                continue

            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if any(term in content for term in search_terms):
                        print(f"[HIT] {fname}")
                        matched_files.append(fname)
            except Exception as e:
                print(f"[ERROR] Could not read {fpath}: {e}")

    return matched_files


def save_results(result_list, search_dir):
    parent_dir = os.path.abspath(os.path.join(search_dir, os.pardir))
    out_path = os.path.join(parent_dir, "search_hits.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for path in result_list:
            f.write(path + "\n")
    print(f"\n✅ Saved results to: {out_path}")


if __name__ == "__main__":
    hits = search_files(SEARCH_DIR, SEARCH_TERMS)
    print(f"\n--- SUMMARY ---")
    print(f"Found {len(hits)} matching files.")
    save_results(hits, SEARCH_DIR)
