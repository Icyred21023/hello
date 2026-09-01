# pip install fonttools
from fontTools.ttLib import TTFont
import os

def _pick_name(name_table, name_id):
    """Prefer typographic names in English (Win platform), then fallbacks."""
    candidates = [n for n in name_table.names if n.nameID == name_id]
    # Prefer Windows Unicode English
    for plat, enc, lang in [(3, 1, 0x0409), (3, 0, 0x0409), (0, 3, 0)]:
        for n in candidates:
            if (n.platformID, n.platEncID, n.langID) == (plat, enc, lang):
                return n.toUnicode()
    # Any remaining candidate
    return candidates[0].toUnicode() if candidates else None

def read_font_names(ttf_path):
    tt = TTFont(ttf_path)
    name_table = tt["name"]
    # Name IDs (important ones):
    # 1 = Family, 2 = Subfamily (Regular/Bold/Italic/Medium)
    # 4 = Full name, 5 = Version, 6 = PostScript name
    # 16 = Preferred Family, 17 = Preferred Subfamily (typographic)
    return {
        "preferred_family": _pick_name(name_table, 16),
        "preferred_subfamily": _pick_name(name_table, 17),
        "family": _pick_name(name_table, 1),
        "subfamily": _pick_name(name_table, 2),
        "full_name": _pick_name(name_table, 4),
        "postscript_name": _pick_name(name_table, 6),
        "version": _pick_name(name_table, 5),
    }

# Example
fonts_list = ["Rajdhani.ttf","Rajdhani Medium.ttf","Rajdhani Bold.ttf","Saira Semi Condensed Medium.ttf","Saira Thin Medium.ttf","Refrigerator Deluxe Bold.ttf","Refrigerator Deluxe Heavy.ttf","Exo Demi Bold.ttf","Exo Light.ttf"]
for font_name in fonts_list:
    path = os.path.join(os.path.dirname(__file__), "fonts", font_name)
    info = read_font_names(path)
    family_for_ui = info["preferred_family"] or info["family"]
    
    print("Font:", font_name, "Family to use:", family_for_ui)
print(info)