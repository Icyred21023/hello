import json, gzip
import os
import cv2

PY_DIR = os.path.dirname(os.path.abspath(__file__))

def save_img(filename=None, img=None):
    if not filename or img is None:
        return None
    path = os.path.join(PY_DIR, 'debug', filename)
    cv2.imwrite(path, img)

def load_img(filename=None):
    if not filename:
        return None
    path = os.path.join(PY_DIR, 'debug', filename)
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return img

def load_gz(path=None):
    if not path or not os.path.exists(path):
        return None
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_gz(path=None, data=None):
    if not path or data is None:
        return None
    path = path + '.gz' if not path.endswith('.gz') else path
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))  # compact style
    
def load_list(path=None):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        items = [line.strip() for line in f if line.strip()]
    return items

def save_list(path=None, items=None):
    if not path or items is None:
        return None
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item + "\n")

def create_path(file=None, folder=""):
    if not file:
        return os.path.join(PY_DIR,folder)
        
    pa = os.path.join(PY_DIR, folder, file)
    return pa
    
def save_json(path=None,data=None):
    if not path or data is None:
        return None
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_json_compact(path=None,data=None):
    if not path or data is None:
        return None
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',',':'), ensure_ascii=True)


def load_json(path=None):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data