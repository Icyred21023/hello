import sys, importlib.metadata as md, builtins, os
import helpers

THIRD_PARTY = set()
STD_LIB_PATH = os.path.dirname(os.__file__)

def is_third_party(module):
    """Check if module lives in site/dist-packages."""
    if not hasattr(module, "__file__") or module.__file__ is None:
        return False
    path = module.__file__
    return "site-packages" in path or "dist-packages" in path

def scan_imports():
    """Scan sys.modules for new third-party imports."""
    for name, module in list(sys.modules.items()):
        if not module or not hasattr(module, "__file__"):
            continue
        if is_third_party(module):
            top = name.split('.')[0]
            THIRD_PARTY.add(top)

def get_package_versions():
    """Return dict of package → version."""
    results = {}
    for pkg in sorted(THIRD_PARTY):
        try:
            results[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            results[pkg] = "?"
    return results

def report(save=True, filename=helpers.create_path("requirements_auto.txt", "gui_assets")):
    """Print and optionally save requirements."""

    scan_imports()
    pkgs = get_package_versions()

    print("\n📦 Third-party modules detected:")
    for pkg, ver in pkgs.items():
        print(f"{pkg}=={ver}")
    print(f"\n💡 Total: {len(pkgs)}\n")

    if save:
        with open(filename, "w", encoding="utf-8") as f:
            for pkg, ver in pkgs.items():
                f.write(f"{pkg}=={ver}\n")
        print(f"✅ Saved to {filename}")

# --- Hook import machinery to track dynamic imports ---
_real_import = builtins.__import__

def tracking_import(name, globals=None, locals=None, fromlist=(), level=0):
    mod = _real_import(name, globals, locals, fromlist, level)
    scan_imports()
    return mod

builtins.__import__ = tracking_import

# --- Automatically write file on program exit ---
#atexit.register(report)