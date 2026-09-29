# updater.py

import os
import requests
import zipfile
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
import queue
import threading
import stat

script_dir = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(script_dir, "version.txt")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Icyred21023/hello/main/version.txt"
REMOTE_ZIP_URL = "https://github.com/Icyred21023/hello/archive/refs/heads/main.zip"
# ============================================================
# UPDATE CLEANUP EXCLUSIONS
# ============================================================
#
# These paths are RELATIVE to script_dir.
#
# EXCLUDED FILES:
#   Put individual files here that should NEVER be deleted.
#
#   Examples:
#       "config.json",
#       "user_settings.json",
#       "data/my_database.json",
#
# EXCLUDED FOLDERS:
#   Put folders here that should NEVER be deleted.
#   EVERYTHING inside an excluded folder is automatically protected,
#   including all subfolders and files.
#
#   Examples:
#       "UserData",
#       "Cache",
#       "assets/custom",
#
# Use forward slashes "/" for nested paths.
# Matching is case-insensitive on purpose.
# ============================================================

DELETE_EXCLUDED_FILES = {
    # "config.json",
    # "user_settings.json",
}

DELETE_EXCLUDED_FOLDERS = {
    ".git",
    
    ".vscode",
    
    
    
    "debug",
    "config",
    "Developer",
    "_Mastery_Sheet_Editor",


    # Add your own below:
    # "UserData",
    # "Custom Assets",
    # "data/cache",
}




import datetime


def normalize_relative_path(path):
    """
    Convert a configured relative path into the correct local OS format.

    Example:
        "config/settings.json"
    becomes:
        "config\\settings.json" on Windows
    """
    path = path.replace("\\", "/").strip("/")
    return os.path.normpath(path)


def remove_path(path):
    """
    Remove either a file, symlink, or directory.
    """
    if not os.path.lexists(path):
        return

    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def copy_preserved_items(current_root, new_root, log=print):
    """
    Copy all protected files/folders from the CURRENT installation
    into the NEW staged installation.

    If the new GitHub build contains something at the same path,
    the CURRENT/local preserved version wins.
    """

    # ---------------------------------------------------------
    # PRESERVED FOLDERS
    # ---------------------------------------------------------
    for configured_path in DELETE_EXCLUDED_FOLDERS:

        relative_path = normalize_relative_path(configured_path)

        src = os.path.join(current_root, relative_path)
        dst = os.path.join(new_root, relative_path)

        if not os.path.isdir(src):
            continue

        log(f"🔒 Preserving folder: {relative_path}")

        # Local/current version completely replaces whatever
        # version may exist in the downloaded build.
        if os.path.lexists(dst):
            remove_path(dst)

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        shutil.copytree(
            src,
            dst,
            copy_function=shutil.copy2
        )

    # ---------------------------------------------------------
    # PRESERVED FILES
    # ---------------------------------------------------------
    for configured_path in DELETE_EXCLUDED_FILES:

        relative_path = normalize_relative_path(configured_path)

        src = os.path.join(current_root, relative_path)
        dst = os.path.join(new_root, relative_path)

        if not os.path.isfile(src):
            continue

        log(f"🔒 Preserving file: {relative_path}")

        if os.path.lexists(dst):
            remove_path(dst)

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        shutil.copy2(src, dst)


def cleanup_old_update_directories(log=print):
    """
    Remove old installation directories left behind by an earlier update.

    This is useful on Windows if a file was locked while the updater
    was still running during the previous update.
    """

    current_root = os.path.abspath(script_dir)
    parent_root = os.path.dirname(current_root)
    app_name = os.path.basename(current_root)

    prefix = f".{app_name}_OLD_UPDATE_"

    try:
        names = os.listdir(parent_root)
    except Exception as e:
        log(f"Could not scan for previous update folders: {e}")
        return

    for name in names:

        if not name.startswith(prefix):
            continue

        path = os.path.join(parent_root, name)

        if not os.path.isdir(path):
            continue

        try:
            log(f"🧹 Removing previous update folder: {path}")
            shutil.rmtree(path)

        except Exception as e:
            # Probably still locked. Not fatal.
            log(
                f"⚠️ Could not remove previous update folder "
                f"{path}: {e}"
            )


# ============================================================
# UPDATE PROGRESS SETTINGS
# ============================================================

# A file/folder operation has overhead even if the file is tiny.
# This makes 10,000 tiny .git files appropriately contribute
# to overall progress instead of being treated as basically 0 MB.
ITEM_WEIGHT_BYTES = 128 * 1024

COPY_CHUNK_SIZE = 1024 * 1024       # 1 MB
DOWNLOAD_CHUNK_SIZE = 1024 * 1024   # 1 MB


def format_bytes(size):
    size = float(size)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            if unit == "B":
                return f"{int(size):,} {unit}"
            return f"{size:,.1f} {unit}"

        size /= 1024

    return f"{size:,.1f} PB"


def normalize_relative_path(path):
    return path.replace("\\", "/").strip("/")


def normalize_compare_path(path):
    return normalize_relative_path(path).lower()


def get_preserve_paths():
    """
    Returns canonical preserve paths.

    If a preserved file/folder is already contained inside a preserved
    folder, it is removed from the explicit list so it isn't copied twice.
    """

    folders = [
        normalize_relative_path(path)
        for path in DELETE_EXCLUDED_FOLDERS
        if path.strip()
    ]

    files = [
        normalize_relative_path(path)
        for path in DELETE_EXCLUDED_FILES
        if path.strip()
    ]

    # Shallow folders first.
    folders.sort(
        key=lambda x: (
            normalize_compare_path(x).count("/"),
            len(x)
        )
    )

    final_folders = []

    for folder in folders:
        compare = normalize_compare_path(folder)

        already_contained = any(
            compare == normalize_compare_path(parent)
            or compare.startswith(normalize_compare_path(parent) + "/")
            for parent in final_folders
        )

        if not already_contained:
            final_folders.append(folder)

    final_files = []

    for file in files:
        compare = normalize_compare_path(file)

        inside_preserved_folder = any(
            compare == normalize_compare_path(folder)
            or compare.startswith(normalize_compare_path(folder) + "/")
            for folder in final_folders
        )

        if not inside_preserved_folder:
            final_files.append(file)

    return final_files, final_folders


def is_preserved_path(relative_path, is_directory=False):
    compare = normalize_compare_path(relative_path)

    preserve_files, preserve_folders = get_preserve_paths()

    if not is_directory:
        for file in preserve_files:
            if compare == normalize_compare_path(file):
                return True

    for folder in preserve_folders:

        folder_compare = normalize_compare_path(folder)

        if compare == folder_compare:
            return True

        if compare.startswith(folder_compare + "/"):
            return True

    return False


# ============================================================
# PROGRESS TRACKING
# ============================================================

class UpdateProgressTracker:

    def __init__(self, emit):
        self.emit = emit

        self.stage_totals = {}
        self.stage_done = {}

        self.current_stage = None
        self.current_title = ""

        self.last_overall = 0.0
        self.last_emit_time = 0.0

    @staticmethod
    def calculate_units(byte_count, item_count):
        return (
            max(0, byte_count)
            +
            max(0, item_count) * ITEM_WEIGHT_BYTES
        )

    def set_stage_total(
        self,
        stage,
        total_bytes=0,
        total_items=0
    ):
        self.stage_totals[stage] = {
            "bytes": max(0, int(total_bytes)),
            "items": max(0, int(total_items)),
        }

        self.stage_done.setdefault(
            stage,
            {
                "bytes": 0,
                "items": 0,
            }
        )

    def start_stage(self, stage, title, detail=""):

        self.current_stage = stage
        self.current_title = title

        self._emit(
            detail=detail,
            force=True
        )

    def add(
        self,
        stage,
        bytes_done=0,
        items_done=0,
        detail="",
        force=False
    ):

        done = self.stage_done.setdefault(
            stage,
            {
                "bytes": 0,
                "items": 0,
            }
        )

        done["bytes"] += max(0, int(bytes_done))
        done["items"] += max(0, int(items_done))

        self.current_stage = stage

        self._emit(
            detail=detail,
            force=force
        )

    def complete_stage(self, stage, detail=""):

        total = self.stage_totals.get(
            stage,
            {
                "bytes": 0,
                "items": 0,
            }
        )

        self.stage_done[stage] = total.copy()

        self.current_stage = stage

        self._emit(
            detail=detail,
            force=True
        )

    def finish(self):

        for stage, total in self.stage_totals.items():
            self.stage_done[stage] = total.copy()

        self.last_overall = 100.0

        self.emit({
            "type": "progress",
            "title": "Update complete",
            "detail": "All update operations completed.",
            "stage_percent": 100.0,
            "overall_percent": 100.0,
            "stage_summary": "Complete",
        })

    def _emit(self, detail="", force=False):

        now = time.monotonic()

        # Prevent thousands of GUI events per second while copying.
        if not force and now - self.last_emit_time < 0.04:
            return

        self.last_emit_time = now

        stage = self.current_stage

        if stage is None:
            return

        total = self.stage_totals.get(
            stage,
            {
                "bytes": 0,
                "items": 0,
            }
        )

        done = self.stage_done.get(
            stage,
            {
                "bytes": 0,
                "items": 0,
            }
        )

        total_units = self.calculate_units(
            total["bytes"],
            total["items"]
        )

        done_units = self.calculate_units(
            done["bytes"],
            done["items"]
        )

        if total_units:
            stage_percent = (
                done_units / total_units
            ) * 100
        else:
            stage_percent = 0

        stage_percent = max(
            0,
            min(100, stage_percent)
        )

        # ----------------------------------------------------
        # OVERALL PROGRESS
        # ----------------------------------------------------

        all_total_units = 0
        all_done_units = 0

        for stage_name, stage_total in self.stage_totals.items():

            stage_done = self.stage_done.get(
                stage_name,
                {
                    "bytes": 0,
                    "items": 0,
                }
            )

            all_total_units += self.calculate_units(
                stage_total["bytes"],
                stage_total["items"]
            )

            all_done_units += self.calculate_units(
                stage_done["bytes"],
                stage_done["items"]
            )

        if all_total_units:
            overall = (
                all_done_units / all_total_units
            ) * 100
        else:
            overall = 0

        # If exact ZIP information changes our estimate,
        # never visually move the progress bar backwards.
        overall = max(
            self.last_overall,
            overall
        )

        overall = min(overall, 99.9)

        self.last_overall = overall

        summary_parts = []

        if total["bytes"]:
            summary_parts.append(
                f"{format_bytes(done['bytes'])} / "
                f"{format_bytes(total['bytes'])}"
            )

        if total["items"]:
            summary_parts.append(
                f"{done['items']:,} / "
                f"{total['items']:,} items"
            )

        summary = "   •   ".join(summary_parts)

        self.emit({
            "type": "progress",
            "title": self.current_title,
            "detail": detail,
            "stage_percent": stage_percent,
            "overall_percent": overall,
            "stage_summary": summary,
        })


# ============================================================
# TKINTER UPDATE WINDOW
# ============================================================

class UpdateProgressWindow:

    def __init__(self, root):

        self.queue = queue.Queue()

        self.root = root

        self.root.title("Updating")
        self.root.geometry("720x265")
        self.root.resizable(False, False)

        # Don't allow user to close while folders are being swapped.
        self.root.protocol(
            "WM_DELETE_WINDOW",
            lambda: None
        )

        self.root.attributes("-topmost", True)
        self.root.deiconify()
        self.root.lift()
        self.root.update_idletasks()
        self.result = None
        self.finished = False

        main = ttk.Frame(
            self.root,
            padding=20
        )

        main.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # CURRENT TASK
        # ----------------------------------------------------

        self.task_title = tk.StringVar(
            value="Preparing update..."
        )

        ttk.Label(
            main,
            textvariable=self.task_title,
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w"
        )

        self.task_bar = ttk.Progressbar(
            main,
            orient="horizontal",
            mode="determinate",
            maximum=100
        )

        self.task_bar.pack(
            fill="x",
            pady=(8, 4)
        )

        self.task_summary = tk.StringVar(
            value=""
        )

        ttk.Label(
            main,
            textvariable=self.task_summary
        ).pack(
            anchor="w"
        )

        self.task_detail = tk.StringVar(
            value=""
        )

        ttk.Label(
            main,
            textvariable=self.task_detail,
            wraplength=680
        ).pack(
            anchor="w",
            pady=(3, 18)
        )

        # ----------------------------------------------------
        # OVERALL
        # ----------------------------------------------------

        self.overall_title = tk.StringVar(
            value="Overall progress   0.0%"
        )

        ttk.Label(
            main,
            textvariable=self.overall_title,
            font=("Segoe UI", 10, "bold")
        ).pack(
            anchor="w"
        )

        self.overall_bar = ttk.Progressbar(
            main,
            orient="horizontal",
            mode="determinate",
            maximum=100
        )

        self.overall_bar.pack(
            fill="x",
            pady=(8, 0)
        )

        self.indeterminate = False

        self.root.after(
            40,
            self.process_queue
        )

    def post(self, event):
        self.queue.put(event)

    def show_analysis(self, text):

        self.task_title.set(
            "Analyzing update"
        )

        self.task_summary.set("")
        self.task_detail.set(text)

        if not self.indeterminate:

            self.task_bar.configure(
                mode="indeterminate"
            )

            self.task_bar.start(12)

            self.indeterminate = True

    def stop_indeterminate(self):

        if self.indeterminate:

            self.task_bar.stop()

            self.task_bar.configure(
                mode="determinate"
            )

            self.indeterminate = False

    def process_queue(self):

        if self.finished:
            return

        try:

            while True:

                event = self.queue.get_nowait()

                event_type = event.get("type")

                if event_type == "analysis":

                    self.show_analysis(
                        event.get(
                            "detail",
                            "Analyzing..."
                        )
                    )

                elif event_type == "progress":

                    self.stop_indeterminate()

                    stage_percent = event.get(
                        "stage_percent",
                        0
                    )

                    overall_percent = event.get(
                        "overall_percent",
                        0
                    )

                    self.task_title.set(
                        event.get(
                            "title",
                            ""
                        )
                    )

                    self.task_summary.set(
                        event.get(
                            "stage_summary",
                            ""
                        )
                    )

                    self.task_detail.set(
                        event.get(
                            "detail",
                            ""
                        )
                    )

                    self.task_bar["value"] = stage_percent
                    self.overall_bar["value"] = overall_percent

                    self.overall_title.set(
                        f"Overall progress   "
                        f"{overall_percent:.1f}%"
                    )

                elif event_type == "done":

                    self.stop_indeterminate()

                    self.result = event["result"]

                    if self.result[0]:

                        self.task_title.set(
                            "Update complete"
                        )

                        self.task_detail.set(
                            "The new version is installed."
                        )

                        self.task_summary.set(
                            "Complete"
                        )

                        self.task_bar["value"] = 100
                        self.overall_bar["value"] = 100

                        self.overall_title.set(
                            "Overall progress   100.0%"
                        )

                    self.root.after(
                        800,
                        self.close
                    )

        except queue.Empty:
            pass

        if not self.finished:

            self.root.after(
                40,
                self.process_queue
            )

    def close(self):

        self.finished = True

        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass


# ============================================================
# INSTALLATION SCANNING
# ============================================================

def scan_current_installation(
    root,
    emit=None
):
    """
    Calculate:

        total bytes in current installation
        total item count
        preserved bytes
        preserved item count

    This allows the overall progress bar to account for deletion
    and preservation before the update actually begins.
    """

    total_bytes = 0
    total_items = 0

    preserve_bytes = 0
    preserve_items = 0

    last_emit = 0

    for current_root, dirs, files in os.walk(root):

        for directory in dirs:

            path = os.path.join(
                current_root,
                directory
            )

            relative = os.path.relpath(
                path,
                root
            )

            total_items += 1

            if is_preserved_path(
                relative,
                is_directory=True
            ):
                preserve_items += 1

        for filename in files:

            path = os.path.join(
                current_root,
                filename
            )

            relative = os.path.relpath(
                path,
                root
            )

            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0

            total_bytes += size
            total_items += 1

            if is_preserved_path(
                relative,
                is_directory=False
            ):
                preserve_bytes += size
                preserve_items += 1

            now = time.monotonic()

            if (
                emit
                and now - last_emit > 0.1
            ):

                emit({
                    "type": "analysis",
                    "detail":
                        f"Scanning current installation...\n"
                        f"{total_items:,} items found   •   "
                        f"{format_bytes(total_bytes)}"
                })

                last_emit = now

    return {
        "total_bytes": total_bytes,
        "total_items": total_items,

        "preserve_bytes": preserve_bytes,
        "preserve_items": preserve_items,
    }


def get_remote_zip_size(url):

    try:

        response = requests.head(
            url,
            allow_redirects=True,
            timeout=10
        )

        response.raise_for_status()

        value = response.headers.get(
            "Content-Length"
        )

        if value:
            return int(value)

    except Exception:
        pass

    return 0


# ============================================================
# CHUNKED FILE COPY
# ============================================================

def copy_file_with_progress(
    src,
    dst,
    tracker,
    relative_name
):

    os.makedirs(
        os.path.dirname(dst),
        exist_ok=True
    )

    copied = 0

    with open(src, "rb") as source:
        with open(dst, "wb") as target:

            while True:

                chunk = source.read(
                    COPY_CHUNK_SIZE
                )

                if not chunk:
                    break

                target.write(chunk)

                copied += len(chunk)

                tracker.add(
                    "preserve",
                    bytes_done=len(chunk),
                    detail=relative_name
                )

    try:
        shutil.copystat(
            src,
            dst
        )
    except OSError:
        pass

    tracker.add(
        "preserve",
        items_done=1,
        detail=relative_name,
        force=True
    )


def remove_existing_path(path):

    if not os.path.lexists(path):
        return

    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)

    else:
        os.remove(path)


def copy_preserved_items(
    current_root,
    new_root,
    tracker
):

    preserve_files, preserve_folders = get_preserve_paths()

    # --------------------------------------------------------
    # FOLDERS
    # --------------------------------------------------------

    for relative_folder in preserve_folders:

        src_root = os.path.join(
            current_root,
            relative_folder
        )

        dst_root = os.path.join(
            new_root,
            relative_folder
        )

        if not os.path.isdir(src_root):
            continue

        if os.path.lexists(dst_root):
            remove_existing_path(dst_root)

        os.makedirs(
            dst_root,
            exist_ok=True
        )

        # Account for root directory itself.
        tracker.add(
            "preserve",
            items_done=1,
            detail=relative_folder,
            force=True
        )

        for current, dirs, files in os.walk(src_root):

            local_relative = os.path.relpath(
                current,
                src_root
            )

            if local_relative == ".":
                destination_current = dst_root
            else:
                destination_current = os.path.join(
                    dst_root,
                    local_relative
                )

            # Directories
            for directory in dirs:

                destination_directory = os.path.join(
                    destination_current,
                    directory
                )

                os.makedirs(
                    destination_directory,
                    exist_ok=True
                )

                display_path = os.path.relpath(
                    os.path.join(
                        current,
                        directory
                    ),
                    current_root
                )

                tracker.add(
                    "preserve",
                    items_done=1,
                    detail=display_path
                )

            # Files
            for filename in files:

                src = os.path.join(
                    current,
                    filename
                )

                relative_inside = os.path.relpath(
                    src,
                    src_root
                )

                dst = os.path.join(
                    dst_root,
                    relative_inside
                )

                display_path = os.path.relpath(
                    src,
                    current_root
                )

                copy_file_with_progress(
                    src,
                    dst,
                    tracker,
                    display_path
                )

    # --------------------------------------------------------
    # INDIVIDUAL FILES
    # --------------------------------------------------------

    for relative_file in preserve_files:

        src = os.path.join(
            current_root,
            relative_file
        )

        dst = os.path.join(
            new_root,
            relative_file
        )

        if not os.path.isfile(src):
            continue

        if os.path.lexists(dst):
            remove_existing_path(dst)

        copy_file_with_progress(
            src,
            dst,
            tracker,
            relative_file
        )


# ============================================================
# TRACKED DIRECTORY DELETION
# ============================================================

def force_delete_file(path):

    try:
        os.remove(path)
        return True

    except PermissionError:

        try:

            os.chmod(
                path,
                stat.S_IWRITE
            )

            os.remove(path)

            return True

        except Exception:
            return False

    except Exception:
        return False


def delete_directory_with_progress(
    root,
    tracker
):
    """
    Deletes the old installation file-by-file so the UI can display
    exactly what is currently being deleted.
    """

    failures = []

    if not os.path.isdir(root):
        tracker.complete_stage("delete")
        return failures

    for current_root, dirs, files in os.walk(
        root,
        topdown=False
    ):

        # ----------------------------------------------------
        # FILES
        # ----------------------------------------------------

        for filename in files:

            path = os.path.join(
                current_root,
                filename
            )

            relative = os.path.relpath(
                path,
                root
            )

            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0

            if not force_delete_file(path):
                failures.append(path)

            # Count it as processed even if deletion failed.
            tracker.add(
                "delete",
                bytes_done=size,
                items_done=1,
                detail=f"Deleting: {relative}"
            )

        # ----------------------------------------------------
        # DIRECTORIES
        # ----------------------------------------------------

        for directory in dirs:

            path = os.path.join(
                current_root,
                directory
            )

            relative = os.path.relpath(
                path,
                root
            )

            try:
                os.rmdir(path)
            except Exception:
                failures.append(path)

            tracker.add(
                "delete",
                items_done=1,
                detail=f"Deleting: {relative}"
            )

    # Root directory itself
    try:
        os.rmdir(root)
    except Exception:
        failures.append(root)

    tracker.add(
        "delete",
        items_done=1,
        detail="Removing old installation directory",
        force=True
    )

    return failures


# ============================================================
# MAIN UPDATE INSTALLER
# ============================================================

def install_update_from_zip(
    zip_url,
    emit
):

    current_root = os.path.abspath(
        script_dir
    )

    parent_root = os.path.dirname(
        current_root
    )

    app_name = os.path.basename(
        current_root
    )

    timestamp = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    work_root = os.path.join(
        parent_root,
        f".{app_name}_UPDATE_WORK_{timestamp}"
    )

    zip_path = os.path.join(
        work_root,
        "update.zip"
    )

    extract_root = os.path.join(
        work_root,
        "extract"
    )

    old_root = os.path.join(
        parent_root,
        f".{app_name}_OLD_UPDATE_{timestamp}"
    )

    tracker = UpdateProgressTracker(
        emit
    )

    log_lines = []

    def log(message):
        message = str(message)
        print(message)
        log_lines.append(message)

    def save_log():

        try:

            log_dir = os.path.join(
                current_root,
                "_update_logs"
            )

            os.makedirs(
                log_dir,
                exist_ok=True
            )

            log_path = os.path.join(
                log_dir,
                f"update_log_{timestamp}.txt"
            )

            with open(
                log_path,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    "\n".join(log_lines)
                )

        except Exception as e:
            print(
                f"[LOG ERROR] {e}"
            )

    try:

        # ====================================================
        # PREFLIGHT ANALYSIS
        # ====================================================

        emit({
            "type": "analysis",
            "detail":
                "Calculating update workload..."
        })

        remote_zip_size = get_remote_zip_size(
            zip_url
        )

        stats = scan_current_installation(
            current_root,
            emit
        )

        current_bytes = stats[
            "total_bytes"
        ]

        current_items = stats[
            "total_items"
        ]

        preserve_bytes = stats[
            "preserve_bytes"
        ]

        preserve_items = stats[
            "preserve_items"
        ]

        # Code/build size without persistent local folders such as .git.
        current_build_bytes = max(
            1,
            current_bytes - preserve_bytes
        )

        current_build_items = max(
            1,
            current_items - preserve_items
        )

        # If GitHub HEAD doesn't tell us ZIP size, use a temporary estimate.
        estimated_download = (
            remote_zip_size
            if remote_zip_size
            else max(
                5 * 1024 * 1024,
                current_build_bytes // 2
            )
        )

        # Exact extraction size becomes available once ZIP is downloaded.
        estimated_extract_bytes = max(
            current_build_bytes,
            estimated_download * 2
        )

        estimated_extract_items = current_build_items

        # ----------------------------------------------------
        # BUILD INITIAL OVERALL WORK PLAN
        # ----------------------------------------------------

        tracker.set_stage_total(
            "download",
            total_bytes=estimated_download
        )

        tracker.set_stage_total(
            "extract",
            total_bytes=estimated_extract_bytes,
            total_items=estimated_extract_items
        )

        tracker.set_stage_total(
            "preserve",
            total_bytes=preserve_bytes,
            total_items=preserve_items
        )

        tracker.set_stage_total(
            "swap",
            total_items=2
        )

        # Entire old installation gets deleted afterward.
        tracker.set_stage_total(
            "delete",
            total_bytes=current_bytes,
            total_items=current_items + 1
        )

        tracker.set_stage_total(
            "finalize",
            total_items=2
        )

        os.makedirs(
            work_root,
            exist_ok=False
        )

        os.makedirs(
            extract_root,
            exist_ok=True
        )

        # ====================================================
        # DOWNLOAD
        # ====================================================

        tracker.start_stage(
            "download",
            "Downloading update",
            "Connecting to GitHub..."
        )

        with requests.get(
            zip_url,
            stream=True,
            timeout=(10, 120)
        ) as response:

            response.raise_for_status()

            actual_download_size = response.headers.get(
                "Content-Length"
            )

            if actual_download_size:

                tracker.set_stage_total(
                    "download",
                    total_bytes=int(
                        actual_download_size
                    )
                )

            with open(
                zip_path,
                "wb"
            ) as target:

                for chunk in response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE
                ):

                    if not chunk:
                        continue

                    target.write(chunk)

                    tracker.add(
                        "download",
                        bytes_done=len(chunk),
                        detail="Downloading GitHub ZIP..."
                    )

        tracker.complete_stage(
            "download",
            "Download complete."
        )

        if not zipfile.is_zipfile(
            zip_path
        ):
            raise RuntimeError(
                "Downloaded file is not a valid ZIP archive."
            )

        # ====================================================
        # NOW WE CAN GET EXACT EXTRACTION TOTALS
        # ====================================================

        with zipfile.ZipFile(
            zip_path,
            "r"
        ) as archive:

            file_infos = [
                info
                for info in archive.infolist()
                if not info.is_dir()
            ]

            exact_extract_bytes = sum(
                info.file_size
                for info in file_infos
            )

            exact_extract_items = len(
                file_infos
            )

            tracker.set_stage_total(
                "extract",
                total_bytes=exact_extract_bytes,
                total_items=exact_extract_items
            )

            # =================================================
            # EXTRACTION
            # =================================================

            tracker.start_stage(
                "extract",
                "Extracting update",
                "Preparing files..."
            )

            extraction_root_abs = os.path.abspath(
                extract_root
            )

            for index, info in enumerate(
                archive.infolist(),
                start=1
            ):

                target_path = os.path.abspath(
                    os.path.join(
                        extract_root,
                        info.filename
                    )
                )

                # ZIP traversal protection.
                if not (
                    target_path == extraction_root_abs
                    or target_path.startswith(
                        extraction_root_abs
                        + os.sep
                    )
                ):
                    raise RuntimeError(
                        f"Unsafe ZIP path: {info.filename}"
                    )

                if info.is_dir():

                    os.makedirs(
                        target_path,
                        exist_ok=True
                    )

                    continue

                os.makedirs(
                    os.path.dirname(
                        target_path
                    ),
                    exist_ok=True
                )

                with archive.open(
                    info,
                    "r"
                ) as source:

                    with open(
                        target_path,
                        "wb"
                    ) as target:

                        while True:

                            chunk = source.read(
                                COPY_CHUNK_SIZE
                            )

                            if not chunk:
                                break

                            target.write(
                                chunk
                            )

                            tracker.add(
                                "extract",
                                bytes_done=len(chunk),
                                detail=info.filename
                            )

                tracker.add(
                    "extract",
                    items_done=1,
                    detail=info.filename,
                    force=True
                )

        tracker.complete_stage(
            "extract",
            "Extraction complete."
        )

        # ====================================================
        # FIND GITHUB ROOT
        # ====================================================

        entries = [
            name
            for name in os.listdir(
                extract_root
            )
            if name != "__MACOSX"
        ]

        directories = [
            name
            for name in entries
            if os.path.isdir(
                os.path.join(
                    extract_root,
                    name
                )
            )
        ]

        if len(directories) != 1:

            raise RuntimeError(
                "Could not determine GitHub repository root."
            )

        new_root = os.path.join(
            extract_root,
            directories[0]
        )

        version_path = os.path.join(
            new_root,
            "version.txt"
        )

        if not os.path.isfile(
            version_path
        ):
            raise RuntimeError(
                "Downloaded build does not contain version.txt."
            )

        with open(
            version_path,
            "r",
            encoding="utf-8"
        ) as f:

            new_version = f.read().strip()

        # ====================================================
        # PRESERVE LOCAL FILES
        # ====================================================

        tracker.start_stage(
            "preserve",
            "Preserving local files",
            "Copying excluded files and folders..."
        )

        copy_preserved_items(
            current_root,
            new_root,
            tracker
        )

        tracker.complete_stage(
            "preserve",
            "All local files preserved."
        )

        # ====================================================
        # SWAP DIRECTORIES
        # ====================================================

        tracker.start_stage(
            "swap",
            "Installing new build",
            "Moving current installation..."
        )

        # Important on Windows.
        os.chdir(
            parent_root
        )

        os.rename(
            current_root,
            old_root
        )

        tracker.add(
            "swap",
            items_done=1,
            detail="Old installation moved aside.",
            force=True
        )

        try:

            os.rename(
                new_root,
                current_root
            )

        except Exception:

            # Rollback.
            if not os.path.exists(
                current_root
            ):

                os.rename(
                    old_root,
                    current_root
                )

            raise

        tracker.add(
            "swap",
            items_done=1,
            detail="New installation activated.",
            force=True
        )

        tracker.complete_stage(
            "swap"
        )

        # ====================================================
        # DELETE OLD INSTALLATION
        # ====================================================

        tracker.start_stage(
            "delete",
            "Deleting old installation",
            "Removing replaced files..."
        )

        delete_failures = delete_directory_with_progress(
            old_root,
            tracker
        )

        tracker.complete_stage(
            "delete",
            (
                "Old installation processed."
                if not delete_failures
                else
                f"{len(delete_failures):,} locked item(s) "
                f"could not be removed."
            )
        )

        # ====================================================
        # FINALIZE
        # ====================================================

        tracker.start_stage(
            "finalize",
            "Finishing update",
            "Removing temporary files..."
        )

        try:
            shutil.rmtree(
                work_root
            )
        except Exception:
            pass

        tracker.add(
            "finalize",
            items_done=1,
            detail="Temporary update files removed.",
            force=True
        )

        log(
            f"Update completed to version {new_version}"
        )

        if delete_failures:

            log(
                f"{len(delete_failures)} old items "
                f"could not be deleted."
            )

            for failed in delete_failures:
                log(
                    f"LOCKED: {failed}"
                )

        save_log()

        tracker.add(
            "finalize",
            items_done=1,
            detail="Update log written.",
            force=True
        )

        tracker.complete_stage(
            "finalize"
        )

        tracker.finish()

        return (
            True,
            f"Update to version {new_version} completed successfully.\n\n"
            "Please relaunch the program."
        )

    except Exception as e:

        error_message = (
            f"❌ Update failed:\n\n{e}"
        )

        log(
            error_message
        )

        # ----------------------------------------------------
        # ROLLBACK
        # ----------------------------------------------------

        try:

            if (
                os.path.isdir(old_root)
                and not os.path.exists(current_root)
            ):

                os.rename(
                    old_root,
                    current_root
                )

        except Exception as rollback_error:

            log(
                f"ROLLBACK FAILED: {rollback_error}"
            )

        try:
            save_log()
        except Exception:
            pass

        try:

            if os.path.isdir(
                work_root
            ):
                shutil.rmtree(
                    work_root
                )

        except Exception:
            pass

        return (
            False,
            error_message
        )


# ============================================================
# RUN UPDATE WITH TK WINDOW
# ============================================================

def run_update_with_progress(
    zip_url,
    root
):

    window = UpdateProgressWindow(root)

    def worker():

        try:

            result = install_update_from_zip(
                zip_url,
                window.post
            )

        except Exception as e:

            result = (
                False,
                f"Unexpected updater error:\n\n{e}"
            )

        window.post({
            "type": "done",
            "result": result
        })

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()

    window.root.mainloop()

    return window.result
     
def get_current_version():
    if not os.path.exists(VERSION_FILE):
        return "0.0.0"
    with open(VERSION_FILE) as f:
        return f.read().strip()


def get_latest_version():
    try:
        response = requests.get(REMOTE_VERSION_URL, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print("Failed to check for update:", e)
        return None



import datetime

def check_for_update(auto_accept=False):
    cleanup_old_update_directories()
    current = get_current_version()
    latest = get_latest_version()
    if latest is None:
        return 
    one, two, three = current.split('.')
    cu = one + two + three
    one2, two2, three2 = latest.split('.')
    la = one2 + two2 + three2

    if int(cu) < int(la):
        print(f"New version available: {latest} (current: {current})")
        proceed = False

        if auto_accept:
            proceed = True
        else:
            # Create temporary root for messagebox
            root = tk.Tk()
            root.title("Updater")
            root.geometry("1x1+0+0")
            root.attributes("-topmost", True)
            root.update_idletasks()

            proceed = messagebox.askyesno(
                "Update Available",
                f"A new version ({latest}) is available.\nUpdate now?",
                icon="question",
                parent=root
            )

        if proceed:

            # NEW
            result, string_ = run_update_with_progress(
    REMOTE_ZIP_URL,
    root
)

            if result:
                title = "✅ Update Success"
                icon = "info"
            else:
                title = "❌ Update Failed"
                icon = "error"

            

            messagebox.showinfo(
                title=title,
                message=string_,
                icon=icon
            )

            
            sys.exit(0)
        else:
            print("Update canceled.")
            return
    else:
        print(f"✅ Running latest version: {current}")
        return

