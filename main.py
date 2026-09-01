
import updater
import dependency_checker
import config
import os
import sys

bNewGui = True

if config.bUseCloudSync:
    from sdb_r2_sync import R2Client, regular_upload_spool_if_present, regular_bootstrap_local_db, admin_download_and_merge_diffs
    import os

    def make_r2():
        return R2Client(
            bucket=config.R2_BUCKET,
            endpoint_url=config.R2_ENDPOINT_URL,
            access_key_id=config.R2_ACCESS_KEY_ID,
            secret_access_key=config.R2_SECRET_ACCESS_KEY,
        )

    def startup_cloud_sync():
        r2 = make_r2()

        if config.IS_ADMIN:
            summary = admin_download_and_merge_diffs(
                r2=r2,
                master_key=config.R2_MASTER_KEY,
                local_admin_db_path=config.sqlite_db_path,  # or separate admin path
                diffs_prefix=config.R2_DIFFS_PREFIX,
            )
            print("[ADMIN MERGE]", summary)
        else:
            # 1) upload pending diffs (if any)
            uploaded_key = regular_upload_spool_if_present(
                r2=r2,
                diffs_prefix=config.R2_DIFFS_PREFIX,
                spool_path=config.DIFF_SPOOL_PATH,
                client_id=config.CLIENT_ID,
                archive_dir=config.DIFF_ARCHIVE_DIR,
            )
            if uploaded_key:
                print("[DIFF UPLOADED]", uploaded_key)

            # 2) bootstrap/refresh local db from cloud checkpoint rules
            summary = regular_bootstrap_local_db(
                r2=r2,
                master_key=config.R2_MASTER_KEY,
                local_working_db=config.sqlite_db_path,
                checkpoints_dir=config.CHECKPOINTS_DIR,
            )
            print("[BOOTSTRAP]", summary)

if config.dependency_check:
    dependency_checker.check_and_install_dependencies()
if config.auto_update == 69:
    config.auto_update = False
    dependency_checker.check_and_install_dependencies()

updater.check_for_update(config.auto_update)

import tkinter as tk

    
def create_desktop_launcher():
    try:
        # Folder where main.py lives
        app_dir = os.path.dirname(os.path.abspath(__file__))
        main_py = os.path.join(app_dir, "main.py")

        # User desktop
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        # Output .bat path
        bat_path = os.path.join(desktop, "MarvelBans Launcher.bat")
        if os.path.exists(bat_path):
            return False
        # Use current Python executable so it works with venv/python install in use
        python_exe = sys.executable

        bat_contents = f'''@echo off
cd /d "{app_dir}"
"{python_exe}" "{main_py}"
pause
'''

        with open(bat_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(bat_contents)

        print(f"[LAUNCHER] Created: {bat_path}")
        return bat_path

    except Exception as e:
        import traceback
        print("[LAUNCHER ERROR]")
        traceback.print_exc()
        return None

if not config.mobile_mode:
    from admin_utils import elevate_if_needed   
    elevate_if_needed()



if __name__ == "__main__":
    ##create_desktop_launcher()wwwwwwwww
    if config.bUseCloudSync:
        startup_cloud_sync()
    if bNewGui:
        import gui_monitor3 as gui
    else:
        import gui
        
    config.debug_menu = True
    gui.start_app()
    
    