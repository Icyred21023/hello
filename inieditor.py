import config
import helpers
import os
import copy
from collections import OrderedDict
import configparser

dev_path = os.path.join(config.script_dir, "Developer")
b_path = os.path.join(dev_path, "b.ini")
d_path = os.path.join(dev_path, "d.ini")
scale_path = os.path.join(dev_path, "Scalability.ini")
merged_path = os.path.join(dev_path, "Merged_Scalability2.ini")


def save_ue_ini(data, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        first_section = True

        for section, content in data.items():
            if not first_section:
                f.write("\n")
            first_section = False

            f.write(f"[{section}]\n")

            # Write scalar keys
            for key, value in content.get("scalars", {}).items():
                f.write(f"{key}={value}\n")

            # Write array keys
            for key, items in content.get("arrays", {}).items():
                for item in items:
                    op = item.get("op", "+")
                    value = item.get("value", "")
                    f.write(f"{op}{key}={value}\n")

            # Write raw lines if any
            for raw_line in content.get("raw", []):
                f.write(f"{raw_line}\n")


def load_ue_ini(path):
    data = OrderedDict()
    current_section = None

    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw_line in enumerate(f, 1):
            line = raw_line.strip()

            if not line or line.startswith(";"):
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                data.setdefault(current_section, {
                    "scalars": OrderedDict(),
                    "arrays": OrderedDict(),
                    "raw": []
                })
                continue

            if current_section is None:
                continue

            if "=" not in line:
                data[current_section]["raw"].append(line)
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if key and key[0] in "+-.!":
                op = key[0]
                real_key = key[1:]
                data[current_section]["arrays"].setdefault(real_key, []).append({
                    "op": op,
                    "value": value,
                    "line": lineno,
                })
            else:
                data[current_section]["scalars"][key] = value

    return data


def load_ini(path):
    config = configparser.ConfigParser()
    config.optionxform = str  # preserve case
    config.read(path)
    return config

base = load_ue_ini(b_path)
default = load_ue_ini(d_path)
active = load_ue_ini(scale_path)


def merge_parent_into_child(parent_cfg, child_cfg):
    """
    Merge two UE-style OrderedDict configs where child inherits from parent.

    Rules:
    - Start from a deep copy of child_cfg.
    - For every section in parent_cfg:
        * If missing in child, add full parent section
        * If present:
            - parent scalar keys overwrite child scalar keys
            - parent array keys overwrite child array keys
            - optionally append raw lines if needed

    Returns a new merged OrderedDict.
    """
    merged = copy.deepcopy(child_cfg) if child_cfg is not None else OrderedDict()

    if parent_cfg is None:
        return merged

    for section, parent_content in parent_cfg.items():
        if section not in merged:
            merged[section] = copy.deepcopy(parent_content)
            continue

        child_content = merged[section]

        # Ensure expected keys exist
        child_content.setdefault("scalars", OrderedDict())
        child_content.setdefault("arrays", OrderedDict())
        child_content.setdefault("raw", [])

        parent_scalars = parent_content.get("scalars", OrderedDict())
        parent_arrays = parent_content.get("arrays", OrderedDict())
        parent_raw = parent_content.get("raw", [])

        # Parent overwrites child scalars
        for key, value in parent_scalars.items():
            child_content["scalars"][key] = value

        # Parent overwrites child arrays by key
        for key, arr_items in parent_arrays.items():
            child_content["arrays"][key] = copy.deepcopy(arr_items)

        # Optional: preserve/add raw lines
        # You can skip this if raw lines are not important for your use case
        if parent_raw:
            child_content["raw"].extend(copy.deepcopy(parent_raw))

    return merged

def flatten_key(cfg):
    merged = copy.deepcopy(cfg) if cfg is not None else OrderedDict()

    if cfg is None:
        return merged

    for section_name in list(merged.keys()):
        if not section_name.endswith("@0"):
            continue

        base_name = section_name[:-2]  # remove "@0"
        names_to_check = [
            base_name + "@1",
            base_name + "@2",
            base_name + "@3",
            base_name + "@Cine",
        ]

        base_section = merged[section_name]
        base_section.setdefault("scalars", OrderedDict())
        base_section.setdefault("arrays", OrderedDict())
        base_section.setdefault("raw", [])

        for other_name in names_to_check:
            if other_name not in merged:
                continue

            other_section = merged[other_name]
            other_scalars = other_section.get("scalars", {})
            other_arrays = other_section.get("arrays", {})

            # Add only scalar keys missing from @0
            for subkey, value in other_scalars.items():
                if subkey not in base_section["scalars"]:
                    base_section["scalars"][subkey] = copy.deepcopy(value)

            # Add only array keys missing from @0
            for subkey, value in other_arrays.items():
                if subkey not in base_section["arrays"]:
                    base_section["arrays"][subkey] = copy.deepcopy(value)

    return merged
            

new = merge_parent_into_child(parent_cfg=default, child_cfg=base)
new = merge_parent_into_child(parent_cfg=active, child_cfg=new)
new_merged = flatten_key(new)

save_ue_ini(new_merged, merged_path)