import re
import tkinter as tk
from tkinter import filedialog
import json
import os

# --- Regex: from `let <letter> = [{` up to the correct `}]` that is
# followed by: newline + optional spaces + "}," + newline (not included in the match)

def save_json(path,data):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "debug", path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_txt(path,data):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "debug", path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(data)

def open_json(path):
    with open(path, "r") as f:
        jsa = json.load(f)
    return jsa

NEWLINE = r'\r'
PATTERN = re.compile(
    
    r'(?<=let [A-Za-z] = )\[\{[\s\S]*?\}\](?=[ \t]*\r?\n\s*\},\r?\n)'

)

PATTERN2 = re.compile(r'\s*image: [^{\r\n]{1,5}\r?\n')


PATTERN3 = re.compile(
    r'fullImage:\s*(?:"[^"\r\n]*"|\{[\s\S]*?\}),\r?\n'
)

PATTERN4 = re.compile(r'tallImage:\s*(?:"[^"\r\n]*"|\{[\s\S]*?\}),\r?\n')

PATTERN5 = re.compile(r'\s*image:\s*(?:"[^"\r\n]*"|\{[\s\S]*?\}),\r?\n')

PATTERN6 = re.compile(r'\s*image:\s*(?:"[^"\r\n]*"|\{[\s\S]*?\}),\r?\n')
PATTERN7 = re.compile(r'description:[^\r\n]*')
PATTERN10 = re.compile(r'descriptions:[^\r\n]*')
PATTERN9 = re.compile(r'meta:[^\r\n]*')
PATTERN11 = re.compile(r'new:[^\r\n]*')

PATTERN8 = re.compile(r',[^A-Za-z0-9]*?\}')

REPLACEMENTS = [
    (re.compile(r'Punisher'), 'The Punisher'),
    (re.compile(r'Rocket Racoon'), 'Rocket Raccoon'),
    (re.compile(r'Mr. Fantastic'), 'Mister Fantastic'),
    (re.compile(r'Hulk'), 'Bruce Banner'),
    (re.compile(r'Jeff'), 'Jeff The Land Shark')
]

THEPUNISHER = re.compile(r'Punisher')
ROCKET = re.compile(r'Rocket Racoon')



def js_to_json(js_str):
        # Remove "let ... =" or "var ... =" or "const ... ="
    #js_str = re.sub(r'^\s*(var|let|const)\s+\w+\s*=\s*', '', js_str)

    # Remove trailing semicolon
    js_str = js_str.strip().rstrip(';')

    # Replace single quotes with double quotes
    #js_str = re.sub(r"'", r'"', js_str)

    # Quote unquoted keys (basic case: keys without quotes before a colon)
    js_str = re.sub(r'(\{|,)\s*([A-Za-z0-9_]+)\s*:', r'\1 "\2":', js_str)

    # Now parse as JSON
    data = json.loads(js_str)
    return data

def insert_new_attributes(old, new):
    for key, subkey in old.items():
        print(key)
        print(subkey)
        dps = old[key]["dps"]
        hps = old[key]["hps"]
        health = old[key]["health"]
        cat = old[key]["category"]
        new[key]["category"] = cat
        new[key]["dps"] = dps
        new[key]["hps"] = hps
        new[key]["health"] = health
        
    return new

def main():
    # Hide the root window
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        title="Select a JS file",
        filetypes=[("JavaScript files", "*.js"), ("All files", "*.*")]
    )
    if not path:
        print("No file selected.")
        return

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Find all matches
    matches = [m.group(0) for m in PATTERN.finditer(text)]  # full matched blocks (without the trailing "},\r\n")
    #var_names = [m.group(1) for m in PATTERN.finditer(text)]  # the single-letter var after "let "

    print(f"Found {len(matches)} match(es).")
    # Example: show first match safely
    if matches:
        print("First match preview:\n", matches[0][:599], "..." if len(matches[0]) > 500 else "", sep="")

    # You now have:
    # - matches: list of strings containing everything from `let <x> = [{` up to the `}]`
    # - var_names: the corresponding single-letter variable names

    # If you need them as variables in code later:
    # return matches, var_names
    first = matches[0] if matches else None
    
    match2 = PATTERN2.sub(NEWLINE, first)
    print("Match without image line:\n", match2[:599])

    match2 = PATTERN3.sub(NEWLINE, match2)
    match2 = PATTERN4.sub(NEWLINE, match2)
    match2 = PATTERN5.sub(NEWLINE, match2)
    match2 = PATTERN7.sub("", match2)
    match2 = PATTERN9.sub("", match2)
    match2 = PATTERN10.sub("", match2)
    match2 = PATTERN11.sub("", match2)
    match2 = PATTERN8.sub(r"\r\n}", match2)
    print("Match without image 22line:\n\n\n", match2[:1000])
    for pattern, replacement in REPLACEMENTS:
        match2 = pattern.sub(replacement, match2)
    save_txt("js.txt", match2)
    cleaned = js_to_json(match2)
    named_dict = {item["name"]: item for item in cleaned}
    save_json("Js to Json.json", named_dict)
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        title="Select Current JSON file",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not path:
        print("No file selected.")
        return
    old = open_json(path)
    new = insert_new_attributes(old, named_dict)
    save_json("Type Matchup NEW.json", new)

    #print(f"Parsed JSON data: {cleaned}")
if __name__ == "__main__":
    main()
