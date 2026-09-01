import os
import sys
import subprocess
from pathlib import Path

# === CONFIG ===
FONT_DIR = Path(r"C:\Users\Corey\Desktop\tt\woff2")  # Folder with your .woff or .woff2 files
OUTPUT_DIR = FONT_DIR / "ttf"                        # Output folder for .ttf files

def install_requirements():
    """Ensure FontTools + Brotli are installed."""
    for pkg in ["fonttools", "brotli"]:
        try:
            __import__(pkg)
        except ImportError:
            print(f"📦 Installing {pkg} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

def convert_woff_to_ttf(woff_path: Path, out_dir: Path):
    """Convert a single .woff (or .woff2) file to .ttf."""
    out_path = out_dir / (woff_path.stem + ".ttf")
    print(f"→ Converting {woff_path.name} → {out_path.name}")
    try:
        cmd = [
            sys.executable, "-m", "fontTools.ttx",
            "-o", str(out_path),
            str(woff_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Done: {out_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {woff_path.name}\n{e.stderr.decode(errors='ignore')}")

def main():
    install_requirements()

    OUTPUT_DIR.mkdir(exist_ok=True)
    woff_files = [f for f in FONT_DIR.glob("*.woff*")]  # Handles .woff and .woff2
    if not woff_files:
        print("❌ No .woff or .woff2 files found in", FONT_DIR)
        return

    print(f"🧩 Found {len(woff_files)} files to convert\n")
    for w in woff_files:
        convert_woff_to_ttf(w, OUTPUT_DIR)

    print(f"\n✅ All conversions complete! TTFs saved in:\n{OUTPUT_DIR}")

if __name__ == "__main__":
    main()
