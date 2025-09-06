import struct
import tkinter as tk
from tkinter import filedialog
import os

def extract_font(path):
    with open(path, "rb") as f:
        data = f.read()

    sigs = {
        b"OTTO": "otf",
        b"\x00\x01\x00\x00": "ttf",
        b"ttcf": "ttc",
        b"wOFF": "woff",
        b"wOF2": "woff2",
    }

    for sig, ext in sigs.items():
        start = data.find(sig)
        if start == -1:
            continue

        try:
            if sig in (b"OTTO", b"\x00\x01\x00\x00"):  # OTF/TTF
                numTables = struct.unpack(">H", data[start+4:start+6])[0]
                max_end = 0
                for i in range(numTables):
                    base = start + 12 + i*16
                    if base+16 > len(data):
                        break
                    offset, length = struct.unpack(">II", data[base+8:base+16])
                    max_end = max(max_end, offset + length)
                font_bytes = data[start:start+max_end]

            elif sig == b"ttcf":  # TrueType Collection
                # Read TTC header: offset table count at 0x08
                numFonts = struct.unpack(">I", data[start+8:start+12])[0]
                # Simplest approach: grab everything until EOF
                font_bytes = data[start:]

            elif sig in (b"wOFF", b"wOF2"):  # WOFF/WOFF2
                total_len = struct.unpack(">I", data[start+8:start+12])[0]
                font_bytes = data[start:start+total_len]

            else:
                continue  # unknown signature

            out_path = path.rsplit(".", 1)[0] + f".{ext}"
            with open(out_path, "wb") as out:
                out.write(font_bytes)
            return out_path

        except Exception as e:
            print(f"❌ Error extracting {path} with sig {sig}: {e}")
            continue

    return None

# Tkinter root hidden
root = tk.Tk()
root.withdraw()

# Pick directory
folder = filedialog.askdirectory(title="Select folder containing .ufont files")
if not folder:
    print("No folder selected.")
else:
    for fname in os.listdir(folder):
        if fname.lower().endswith(".ufont"):
            fpath = os.path.join(folder, fname)
            out = extract_font(fpath)
            if out:
                print(f"✅ Extracted: {out}")
            else:
                print(f"❌ No known font signature found in {fpath}")
