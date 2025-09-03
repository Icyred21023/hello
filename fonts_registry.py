# fonts_registry.py
import os, ctypes, atexit

FR_PRIVATE = 0x10
FR_NOT_ENUM = 0x20  # (not used here)
_gdi32 = ctypes.windll.gdi32
_registered_paths = set()

def register_ttf_private(ttf_path: str) -> bool:
    """Load a TTF privately for this process. Returns True if added (or already loaded)."""
    path = os.path.abspath(ttf_path)
    if path in _registered_paths:
        return True
    added = _gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
    if added > 0:
        _registered_paths.add(path)
        return True
    return False  # path bad or font failed to load

def remove_registered_fonts():
    for path in list(_registered_paths):
        _gdi32.RemoveFontResourceExW(path, FR_PRIVATE, 0)
        _registered_paths.discard(path)

atexit.register(remove_registered_fonts)