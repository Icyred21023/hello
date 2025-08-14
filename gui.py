import tkinter as tk
from PIL import ImageTk, Image, ImageGrab
import os
import sys
import time
from main3 import HeroMatch
import numpy as np
import config
if not config.mobile_mode:
    
    import win32gui
    import win32con
    import win32api
    import win32process
    import win32com.client
    import ctypes
    import keyboard
lock = None
bhidden = False
bdebug_menu = False
is_clickthrough = False
indicator_label = None
hwnd = None
global_random_matchup = False
global_random_ban = False
global_dex = False
global_debugmode = False
global_debugflag = False
main = None
var1 = None
var2 = None
trigger2_func = None
trigger_func = None
root = None
cb1 = None
cb2 = None
cb3 = None

fonts = {}

def handle_f10():
    global main, var2, trigger2_func, root, is_clickthrough, indicator_label
    try:

        if is_clickthrough:
                    make_interactive()
                    is_clickthrough = False
                    if indicator_label:
                        indicator_label.config(text="", bg="#1C2026")
                        indicator_label.update_idletasks()

        if main and main.winfo_ismapped() and root and root.winfo_exists():
            # Schedule both actions in the Tkinter main thread
            root.after(0, lambda: (root.destroy(), trigger2_func(var2.get())))
    except Exception as e:
        print(f"F10 error: {e}")

def handle_f8():
    global main, var1, trigger_func, root, is_clickthrough, indicator_label
    try:

        if is_clickthrough:
                    make_interactive()
                    is_clickthrough = False
                    if indicator_label:
                        indicator_label.config(text="", bg="#1C2026")
                        indicator_label.update_idletasks()

        if main and main.winfo_ismapped() and root and root.winfo_exists():
            # Schedule both actions in the Tkinter main thread
            root.after(0, lambda: (root.destroy(), trigger_func(var1.get())))
    except Exception as e:
        print(f"F8 error: {e}")

def toggle_lock(lock_button):
    current = lock_button.cget("text")

    print(current)
    lock_button.config(text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)")
    toggle_clickthrough()
        
def make_clickthrough():
    global hwnd
    if not config.mobile_mode:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    print("Click-through ENABLED")

def make_interactive():
    global hwnd
    if not config.mobile_mode:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    print("Click-through DISABLED")

def widget_exists(widget):
    try:
        return bool(widget.winfo_exists())
    except:
        return False

def toggle_clickthrough():
    global is_clickthrough, indicator_label, lock
    if is_clickthrough:
        make_interactive()
        if indicator_label:
            indicator_label.config(text="")
            indicator_label.update_idletasks()
            indicator_label.update()
        if widget_exists(lock):
            
        
            current = lock.cget("text")

            
            lock.config(text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)")
    else:
        make_clickthrough()
        if indicator_label:
            indicator_label.config(text="🔒", fg="red")
            indicator_label.update_idletasks()
            indicator_label.update()
        if widget_exists(lock):
            
            current = lock.cget("text")

            
            lock.config(text="Unlock(F6)" if current == "Lock(F6)" else "Lock(F6)")
            
    is_clickthrough = not is_clickthrough


def scale_font(scale, size):
    return int(size / scale)                            
def change_color(value):
    value = int(value)
    if value > 2:
        return "#3ecbff"
    elif value > 0:
        return "#5de791"
    elif value == 0:
        return "white"
    elif value  > -3:
        return "#FFA800"
    else:
        return "#FF3C3C"
    
    
def show_suggestion_gui(results, image_map,map, blue_dict,red_dict):
    global bhidden, indicator_label
    blue_result, suggest_result, alt_result, red_result = results
    origs_score = blue_result.total_score
    new_scores  = suggest_result.total_score
    alt_scores   = alt_result.total_score
    red_scores1 = red_result.total_score
    red_scores2 = red_result.total_score2
    red_scores3 = red_result.total_score3
    return_data = {}
    bhidden = False
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    x = (screen_width // 2) - 700
    root.geometry(f"+{x}+0")
    root.withdraw()

    win = tk.Toplevel(root)
    win.title("")
    def go_back():
        blue = []
        red = []
        for i in range(1, 7):
            b_member = getattr(blue_result, str(i))
            r_member = getattr(red_result, str(i))
        #     s = b_member.suggestion
        #     if not s:
        #         s = b_member.character
        #         name = s.name
        #     else:
        #         name = s.original if s else member.character.name
        #     blue.append(HeroMatch(name, name, 10, False))
        #     name = r_member.character.name
        #     red.append(HeroMatch(name, name, 10, False))
        # return_data["teams"] = (blue, red)
        root.destroy()



    def toggle_hide():
        global bhidden
        bhidden = not bhidden
        if bhidden:
            main_frame.pack_forget()
            hide_btn2.config(text="Show")
            
        else:
            main_frame.pack(padx=0, pady=0)
            hide_btn2.config(text="Hide")
        win.update_idletasks()
        

    win.overrideredirect(True)
    title_bar2 = tk.Frame(win, bg="#13151A", relief="solid", width=1135,height=17)
    title_bar2.pack(fill="x", side="top",ipady=3)
    title_bar2.pack_propagate(False)
    close_btn2 = tk.Button(title_bar2, command=lambda: close3(root),text="X", width=2,height=1,fg="white", relief="flat",bg="#141420", font=("Lucida Console", fonts[12]), cursor="hand2")
    close_btn2.pack(side="right", padx=0)
    hide_btn2 = tk.Button(title_bar2, command=toggle_hide,text="Hide", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[12]), cursor="hand2")
    hide_btn2.pack(side="right", padx=10)
    back = tk.Button(title_bar2, command=go_back,text="Back", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[12]), cursor="hand2")
    back.pack(side="right", padx=10)
    global lock
    lock = tk.Button(title_bar2, command=toggle_clickthrough,text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[8]), cursor="hand2")
    lock.pack(side="right", padx=10)

    indicator_label = tk.Label(title_bar2, text="", fg="white", bg="#13151A", font=("Arial", fonts[12]))
    indicator_label.pack(side="left",padx=0)
    close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
    close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))

    hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
    hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
    back.bind("<Enter>", lambda e: back.config(bg="#31314D"))
    back.bind("<Leave>", lambda e: back.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    
    win.geometry(f"+{x}+0")
    win.title("Team Suggestion Comparison")
    win.configure(bg="#1C2026")
    win.attributes("-topmost", True)
    win.grab_set()

    def get_image(name):
        img_obj = image_map.get(name)
        if not img_obj:
            img_obj = image_map.get("Default")
        if img_obj:
            resized = img_obj.copy()
            resized.thumbnail((128, 128))
            return ImageTk.PhotoImage(resized)
        return None

    main_frame = tk.Frame(win, bg="#1C2026")
    main_frame.pack(padx=0, pady=0)
    light_blue = "#456093"
    dark_blue = "#2C334B"
    suggest_dark = "#354569"
    suggest_blue = "#6D9EC2"
    alt_dark = "#2A4A32"
    alt_light = "#579967"
    light_red = "#A15444"
    dark_red = "#6B382E"
    bord_color = "#1C2026"
    blue_score = "#4E648A"
    suggest_score = "#465C8C"
    green_score = "#41734D"
    red_score = "#854539"

    original_frame = tk.Frame(main_frame, bg=dark_blue, padx=10, pady=10)
    suggestion_frame = tk.Frame(main_frame, bg=suggest_dark, padx=10, pady=10)
    alt_frame = tk.Frame(main_frame, bg=alt_dark, padx=10, pady=10)
    red_frame = tk.Frame(main_frame, bg=dark_red, padx=10, pady=10)

    original_frame.grid(row=0, column=0, sticky="nw")
    suggestion_frame.grid(row=0, column=1, sticky="nw")
    alt_frame.grid(row=0, column=2, sticky="nw")
    red_frame.grid(row=0, column=3, sticky="nw")
    if config.dex:
        string = "Dexerto Counters"
    else:
        string = "PeakRivals Counters"

    tk.Label(original_frame, text="Current Team", font=("Arial", fonts[14], "bold"), fg="white", bg=dark_blue).pack()
    tk.Label(suggestion_frame, text=string, font=("Arial", fonts[14], "bold"), fg="white", bg=suggest_dark).pack()
    tk.Label(alt_frame, text="Full Counter Team", font=("Arial", fonts[14], "bold"), fg="white", bg=alt_dark).pack()
    tk.Label(red_frame, text="Enemy Team", font=("Arial", fonts[14], "bold"), fg="white", bg=dark_red).pack()
    score_totals_list = []



    for i in range(1, 7):
        # Blue column (col 1)
        b_member = getattr(blue_result, str(i))
        s_member = getattr(suggest_result, str(i))
        a_member = getattr(alt_result, str(i))
        r_member = getattr(red_result, str(i))



        orig_name = b_member.name
        orig_score = b_member.matchup_score
        new_name = s_member.name
        new_score = s_member.matchup_score
        alt_name = a_member.name
        alt_score = a_member.matchup_score
        red_name = r_member.name
        red_score1 = r_member.matchup_score
        red_score2 = r_member.matchup_score2
        red_score3 = r_member.matchup_score3
        
        def get_alternate_char_name(dict, hero_name):
            key = dict[i-1]
            base_name = key["base_name"]
            full_name = key["full_name"]
            if base_name != full_name:
                if base_name == hero_name:
                    return full_name
            return base_name



        orig_name2 = get_alternate_char_name(blue_dict, orig_name)
        red_name2 = get_alternate_char_name(red_dict, red_name)

        

        # === Column 1: Original Blue ===
        row_orig = tk.Frame(original_frame, bg=dark_blue)
        row_orig.pack(fill="x", pady=6,padx = 1)

        orig_img = get_image(orig_name)
        img_obj = get_image_from_map(map, orig_name, orig_name2)
        resized = img_obj.copy()
        resized.thumbnail((128, 128))
        orig_img = ImageTk.PhotoImage(resized)
        if orig_img:
            outer = tk.Label(row_orig, width=124, height=124,image=orig_img, bg=light_blue, highlightthickness=2,
                     highlightbackground=bord_color)
            outer.pack(side="left")
            outer.pack_propagate(False)
            row_orig.image = orig_img
        scolor = change_color(orig_score)
        tk.Label(row_orig, text=f"{orig_score:+}", highlightthickness=2,
                 highlightbackground=bord_color, fg=scolor, bg=blue_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
        
        if s_member and new_name != orig_name:
            # Draw arrow
            tk.Label(row_orig, text="➡", fg="#08FCFC", relief="sunken", bg=dark_blue,
                     font=("Courier New", fonts[60], "bold")).pack(side="left", padx=(20, 0))

                # === Column 2: Primary Suggestion ===
        
        row_sugg = tk.Frame(suggestion_frame, bg=suggest_dark)
        row_sugg.pack(fill="x", padx=10, pady=6)

        if s_member and orig_name != new_name:
            # Draw arrow
            #tk.Label(row_sugg, text="➡", fg="#08FCEF", bg=suggest_dark,
                     #font=("Courier New", fonts[26], "bold")).pack(side="left", padx=(0, 15))

            # Suggestion image
            sugg_img = get_image(new_name)
            if sugg_img:
                img_label = tk.Label(row_sugg, width=124, height=124,image=sugg_img, bg=suggest_blue,
                                     highlightthickness=2, highlightbackground=bord_color)
                img_label.image = sugg_img
                img_label.pack(side="left")
                
                img_label.pack_propagate(False)
            else:
                tk.Label(row_sugg, text=new_name, fg="white", bg=suggest_blue).pack(side="left")

            # Suggestion score
            scolor = change_color(new_score)
            tk.Label(row_sugg, text=f"{new_score:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=suggest_score,
                     font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
            

        else:
            # No replacement or replacement == original — reserve space
            spacer = tk.Frame(row_sugg, width=124 + 60, height=124, bg=suggest_dark)
            spacer.pack_propagate(False)
            spacer.pack(side="left",pady=4)
            
            #tk.Label(spacer, text="No suggestion", fg="white", bg=dark_blue).pack(anchor="center")

        # === Column 3: Alternative Suggestion ===
        alt = a_member
        row_alt = tk.Frame(alt_frame, bg=alt_dark)
        row_alt.pack(fill="x", padx= 25,pady=6)
        if alt:
            alt_img = get_image(alt_name)
            if alt_img:
                outer = tk.Label(row_alt, width=124, height=124,image=alt_img, bg=alt_light, highlightthickness=2,
                         highlightbackground=bord_color)
                outer.pack(side="left")
                outer.pack_propagate(False)
                row_alt.image = alt_img
            scolor = "white"
            scolor = change_color(alt_score)
            
            tk.Label(row_alt, text=f"{alt_score:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=green_score,
                     font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
        else:
            tk.Label(row_alt, text="No alt", fg="white", bg=alt_dark).pack()

        # === Column 4: Red Team ===
        
        red_row = tk.Frame(red_frame, bg=dark_red)
        red_row.pack(fill="x", pady=6, padx=25)

        red_img = get_image(red_name)
        ii = get_image_from_map(map, red_name, red_name2)
        resized = ii.copy()
        resized.thumbnail((128, 128))
        red_img = ImageTk.PhotoImage(resized)
        if red_img:
            outer = tk.Label(red_row,width=124, height=124, image=red_img, bg=light_red, highlightthickness=2,
                     highlightbackground=bord_color)
            outer.pack(side="left")
            outer.pack_propagate(False)
            red_row.image = red_img
        scolor = "white"
        scolor = change_color(red_score1)
        
        tk.Label(red_row, text=f"{red_score1:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=red_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
        scolor = "white"
        scolor = change_color(red_score2)
        
        tk.Label(red_row, text=f"{red_score2:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=red_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
        scolor = change_color(red_score3)
        tk.Label(red_row, text=f"{red_score3:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=red_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
        
        red_scores1 = round(red_scores1,1)
        red_scores2= round(red_scores2,1)
        red_scores3= round(red_scores3,1)
        alt_scores= round(alt_scores,1)
        new_scores=round(new_scores,1)
        origs_score= round(origs_score,1)
        

    origbg = "#5B6A9C"
    newbg = "#556FA8"
    altbg = "#4A8258"
    redbg = "#A15445"

    #Total Scores - Original Score
    tot_orig = tk.Frame(original_frame, bg="#5B6A9C", highlightthickness=2,
                     highlightbackground=bord_color)
    tot_orig.pack(fill="x", pady=(6,0),padx = 0, ipady=10)
    #Stats
    stat_orig = tk.Frame(original_frame, bg="#5B6A9C", highlightthickness=2,
                     highlightbackground=bord_color)
    stat_orig.pack(fill="x", pady=(6,0),padx = 0, ipady=10)
    
    tk.Label(tot_orig, text="Total Score: ", font=("Arial", fonts[16], "bold"), fg="white", bg="#5B6A9C").pack(side="left")
    scolor = change_color(origs_score)
    tk.Label(tot_orig, text=f"{origs_score:+}", highlightthickness=2,
                highlightbackground=bord_color, fg=scolor, bg=blue_score,
                font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
    # Total - New Blue
    tot_new = tk.Frame(suggestion_frame, bg="#556FA8", highlightthickness=2,
                     highlightbackground=bord_color)
    tot_new.pack(fill="x", pady=(6,0),padx = 2, ipady=10)
    
    # Statsl - New Blue
    stat_new = tk.Frame(suggestion_frame, bg="#556FA8", highlightthickness=2,
                     highlightbackground=bord_color)
    stat_new.pack(fill="x", pady=(6,0),padx = 2, ipady=10)
    
    tk.Label(tot_new, text="Total Score: ", font=("Arial", fonts[16], "bold"), fg="white", bg="#556FA8").pack(side="left")
    scolor = change_color(new_scores)
    tk.Label(tot_new, text=f"{new_scores:+}", highlightthickness=2,
                highlightbackground=bord_color, fg=scolor, bg=suggest_score,
                font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
    # Total - Alt Blue
    row_alt_tot = tk.Frame(alt_frame, bg="#4A8258", highlightthickness=2,
                     highlightbackground=bord_color)
    row_alt_tot.pack(fill="x", pady=(6,0),padx = 5, ipady=10)
    
    # Statsl - Alt Blue
    stat_alt = tk.Frame(alt_frame, bg="#4A8258", highlightthickness=2,
                     highlightbackground=bord_color)
    stat_alt.pack(fill="x", pady=(6,0),padx = 5, ipady=10)
    
    tk.Label(row_alt_tot, text="Total Score: ", font=("Arial", fonts[16], "bold"), fg="white", bg="#4A8258").pack(side="left")
    scolor = change_color(alt_score)
    tk.Label(row_alt_tot, text=f"{alt_scores:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=green_score,
                     font=("Courier New", fonts[16], "bold")).pack(side="left", padx=12)
    # Total - red 1
    red1 = tk.Frame(red_frame, bg="#A15445", highlightthickness=2,
                     highlightbackground=bord_color)
    red1.pack(fill="x", pady=(6,0),padx = 3, ipady=10)
    
    # Stats - red 1
    stat_red = tk.Frame(red_frame, bg="#A15445", highlightthickness=2,
                     highlightbackground=bord_color)
    stat_red.pack(fill="x", pady=(6,0),padx = 3, ipady=10)
    
    def get_color(value, stat_type, thresholds):
        t = thresholds[stat_type]
        avg = t["avg"]
        tolerance = 0.005 * avg  # 5% of average
    
        # First: check if value is within ±5% of avg
        if abs(value - avg) <= tolerance:
            return "#ffffff"  # white
    
        # Then use original logic
        if value <= t["low_mid"]:
            return "#ff3c3c"  # red
        elif value <= avg:
            return "#FFa800"  # yellow
        elif value <= t["high_mid"]:
            return "#5de791"  # green
        else:
            return "#3ecbff"  # blue

    
    def build_color_thresholds(results):
        # results is an iterable of team objects
        stats = {"dps": [], "hps": [], "health": []}
    
        # Collect totals from each team
        for team in results:
            stats["dps"].append(team.dps)
            stats["hps"].append(team.hps)
            stats["health"].append(team.health)
    
        thresholds = {}
        for key, values in stats.items():
            min_v = min(values)
            max_v = max(values)
            avg = sum(values) / len(values)
            half_range = (max_v - min_v) / 2
    
            thresholds[key] = {
                "min": min_v,
                "max": max_v,
                "avg": avg,
                "low_mid": avg - 0.5 * half_range,
                "high_mid": avg + 0.5 * half_range
            }
    
        return thresholds

    
            
              

    
    #def build_color_thresholds():
#        import copy
#    # # Collect values
#        stats = {"dps": [], "hps": [], "health": []}
#        score_totals = {}
#        for i, item in results:
#            dps = item.dps
#            hps = item.hps
#            health = item.health
#            js = {"dps": dps,
#            "hps":hps,
#            "health":health}
#            score_totals[i] = copy.deepcopy(js)
#            
#    
#        for team_data in score_totals.values():
#            for member_stats in team_data.values():
#                 for key in stats:
#                    stats[key].append(member_stats[key])
#    
#        thresholds = {}
#    
#        for key, values in stats.items():
#             min_v = min(values)
#             max_v = max(values)
#             avg = sum(values) / len(values)
#             half_range = (max_v - min_v) / 2
#    
#             thresholds[key] = {
#                 "min": min_v,
#                 "max": max_v,
#                 "avg": avg,
#                 "low_mid": avg - 0.5 * half_range,
#                 "high_mid": avg + 0.5 * half_range
#              }
#    
#        return thresholds

            
    
    def create_stat_frames(frame,color,num,back,bg2):
        up = tk.Frame(frame, bg=back, highlightthickness=0,highlightbackground=bord_color)
        up.pack(fill="both", side="top",pady=5)
        mid= tk.Frame(frame, bg=back, highlightthickness=0,highlightbackground=bord_color)
        mid.pack(fill="both", side="top",pady=5)
        bot= tk.Frame(frame, bg=back, highlightthickness=0,highlightbackground=bord_color)
        bot.pack(fill="both", side="top",pady=5)
        index = int(num) - 1
        if color == 'Red':
            index = 3
        teaam = results[index]    
        dps = teaam.dps
        hps = teaam.hps
        health = teaam.health
        fg_dps = get_color(dps,"dps",thresholds)
        fg_hps = get_color(hps,"hps",thresholds)
        fg_health = get_color(health,"health",thresholds)
        tk.Label(up, text="DPS Total: ", font=("Arial", fonts[14], "bold"), fg="white", bg=back).pack(side="left")
        tk.Label(up, text=dps, font=("Courier New", fonts[16], "bold"), fg=fg_dps,highlightthickness=2, highlightbackground=bord_color,bg=bg2).pack(side="left",padx=10)
        tk.Label(mid, text="HPS Total: ", font=("Arial", fonts[14], "bold"), fg="white", bg=back).pack(side="left")
        tk.Label(mid, text=hps, font=("Courier New", fonts[16], "bold"), fg=fg_hps, highlightthickness=2, highlightbackground=bord_color,bg=bg2).pack(side="left",padx=10)
        tk.Label(bot, text="Health Total: ", font=("Arial", fonts[14], "bold"), fg="white", bg=back).pack(side="left")
        tk.Label(bot, text=health, font=("Courier New", fonts[16], "bold"), fg=fg_health,highlightthickness=2, highlightbackground=bord_color,bg=bg2).pack(side="left",padx=10)
        
        
    
    
    scolor = change_color(red_scores1)
    tk.Label(red1, text="Total Scores: ", font=("Arial", fonts[16], "bold"), fg="white", bg="#A15445").pack(side="left")
    tk.Label(red1, text=f"{red_scores1:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=red_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
    # Total - red 2
    
    scolor = change_color(red_scores2)
    tk.Label(red1, text=f"{red_scores2:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=red_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
    # Total - red 3
    
    scolor = change_color(red_scores3)
    tk.Label(red1, text=f"{red_scores3:+}", highlightthickness=2,
                     highlightbackground=bord_color, fg=scolor, bg=red_score,
                 font=("Courier New", fonts[16], "bold")).pack(side="left", padx=6)
    thresholds = build_color_thresholds(results)
    
    create_stat_frames(stat_orig,"Blue","1",origbg,blue_score)
    create_stat_frames(stat_new,"Blue","2",newbg,suggest_score)
    create_stat_frames(stat_alt,"Blue","3",altbg,green_score)
    create_stat_frames(stat_red,"Red","1",redbg,red_score)
    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()
    win.update_idletasks()
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, win.title())
    #make_clickthrough()
    win.geometry("")
    root.mainloop()
    return return_data.get("teams")


def show_countdown():
    global indicator_label
    root = tk.Tk()
    root.title("Scoreboard Scan in...")
    root.configure(bg="#2C334B")
    root.overrideredirect(True)
    screen_width = root.winfo_screenwidth()
    x = screen_width // 2
    root.geometry(f"200x100+{x}+0")
    root.attributes("-topmost", True)
    indicator_label = tk.Label(root, text="", fg="white", bg="#2C334B", font=("Arial", fonts[8]))
    indicator_label.pack(anchor="w")
    labela = tk.Label(root, text="Hold\nTAB",bg="#2C334B", fg="yellow",font=("Lucida Console", fonts[14],"bold"))
    labela.pack(expand=True,anchor="center",pady=0)
    label = tk.Label(root, text="",bg="#2C334B", fg="white",font=("Arial", fonts[20],"bold"))
    label.pack(expand=True,pady=5)

    def update_countdown(i):
        if i > 0:
            if not is_clickthrough:
                toggle_clickthrough()
            label.config(text=str(i))
            root.update()
            root.after(1000, update_countdown, i - 1)
        else:
            if is_clickthrough:
                toggle_clickthrough()
            root.destroy()

    update_countdown(3)
    
    root.mainloop()

def get_image_from_map(image_map, base_name, full_name):
    variants = image_map.get(base_name, [])
    for variant in variants:
        if variant["name"] == full_name:
            return variant["image"]
    return image_map["Default"][0]["image"]  # fallback

def change_character_dropdown(match, image_map, label_widget):
    top = tk.Toplevel()
    top.attributes("-topmost", True)
    top.title("Change Character")
    top.grab_set()  # Make it modal

    tk.Label(top, text=f"Current: {match.name}").pack(pady=(10, 2))

    hero_names = sorted(image_map.keys())
    selected_hero = tk.StringVar(value=match.name)

    # Image preview area
    img_label = tk.Label(top)
    img_label.pack(pady=5)

    def update_image(*args):
        hero = selected_hero.get()
        img_obj = image_map.get(hero, image_map.get("Default"))
        if img_obj:
            preview = img_obj.copy()
            preview.thumbnail((128, 128))
            photo = ImageTk.PhotoImage(preview)
            img_label.configure(image=photo)
            img_label.image = photo
        else:
            img_label.configure(text="No image found", image="")

    selected_hero.trace_add("write", update_image)

    dropdown = tk.OptionMenu(top, selected_hero, *hero_names)
    dropdown.pack(pady=5)

    def submit():
        match.name = selected_hero.get()
        # Refresh the image in the original GUI
        new_img = image_map.get(match.name, image_map.get("Default")).copy()
        new_img.thumbnail((128, 128))
        new_photo = ImageTk.PhotoImage(new_img)
        label_widget.configure(image=new_photo)
        label_widget.image = new_photo
        top.destroy()

    tk.Button(top, text="OK", command=submit).pack(pady=(0, 10))

    update_image()
    top.wait_window()  # Block interaction with main window

def convert_color(value):
    mapping = {
        "#456093": "#2C334B",  # bg_c blue
        "#A15444": "#6B382E",  # bg_c red
    }
    return mapping.get(value, value)  # Return the mapped value, or original if not found

def change_character(match, image_map, label_widget,bg_c):
    import tkinter as tk
    from PIL import Image, ImageTk
    bg_dark = convert_color(bg_c)
    top = tk.Toplevel()
    top.configure(bg=bg_dark)
    top.attributes("-topmost", True)
    top.title("Change Character")
    top.grab_set()  # Make it modal
    topb = tk.Frame(top, bg=bg_dark)
    topb.pack( side="top")
    left = tk.Frame(topb, bg=bg_dark)
    left.pack(fill="y", padx=15,side="left")

    right = tk.Frame(topb, bg=bg_dark)
    if match.score > 50:
        right.pack(fill="y",padx=15, side="right")

    tk.Label(left, fg="white",bg=bg_dark,text=f"Current: {match.name}",font=("Arial",12,"bold")).pack(pady=(10, 2), anchor="center")

    selected_hero = tk.StringVar(value=match.name)

    # Image preview area
    img_label = tk.Label(left,bg=bg_c,relief="raised")
    img_label.pack(pady=5, anchor="center")
    if match.score > 50:
        tk.Label(right,fg="white",bg=bg_dark,text=f"Scanned:",font=("Arial",12,"bold"), anchor="s").pack(pady=(10, 2), anchor="s")
        img_label2 = tk.Label(right,bg=bg_c,relief="raised", anchor="s")
        img_label2.pack(pady=5, anchor="s")

    def update_image(*args):
        hero = selected_hero.get()
        img_obj = image_map.get(hero, image_map.get("Default"))
        if img_obj:
            preview = img_obj.copy()
            preview.thumbnail((128, 128))
            photo = ImageTk.PhotoImage(preview)
            img_label.configure(image=photo, bg = bg_c)
            img_label.image = photo
        else:
            img_label.configure(text="No image found", image="")
        if match.score > 50:
            cropped = match.image
            cropped.thumbnail((128, 128))
            img2 = ImageTk.PhotoImage(cropped)
            
            img_label2.configure(image=img2, bg = bg_c)
            img_label2.image = img2

    selected_hero.trace_add("write", update_image)

    # --- 6x6 Icon Grid ---
    grid_frame = tk.Frame(top, bg=bg_dark)
    grid_frame.pack(pady=10)

    thumbnails = {}
    max_cols = 6
    row = col = 0

    for hero_name in sorted(image_map.keys()):
        if hero_name == "Unknown":
            continue
        img_obj = image_map[hero_name]
        if not img_obj:
            continue

        # Make 64x64 thumbnail
        thumb = img_obj.copy()
        thumb.thumbnail((64, 64))
        thumb_img = ImageTk.PhotoImage(thumb)
        thumbnails[hero_name] = thumb_img  # Prevent garbage collection

        def make_click_callback(name=hero_name):
            def callback():
                selected_hero.set(name)  # Triggers preview update
                submit()
            return callback

        btn = tk.Button(grid_frame, bg=bg_c, image=thumb_img, command=make_click_callback(), width=64, height=64)
        btn.grid(row=row, column=col, padx=3, pady=3)

        def on_enter(event, name=hero_name, button=btn):
            img_obj = image_map[name]
            thumb = img_obj.copy()
            thumb.thumbnail((64, 64))
            base_img = thumb.convert("RGBA")
            overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 100))
            combined = Image.alpha_composite(base_img, overlay)
            hover_img = ImageTk.PhotoImage(combined)

            button.configure(image=hover_img)
            button.image = hover_img  # prevent garbage collection

        def on_leave(event, name=hero_name, button=btn):
            img_obj = image_map[name]
            thumb = img_obj.copy()
            thumb.thumbnail((64, 64))
            normal_img = ImageTk.PhotoImage(thumb)

            button.configure(image=normal_img)
            button.image = normal_img  # prevent garbage collection
            

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        col += 1
        if col >= max_cols:
            col = 0
            row += 1


    def submit():
        match.name = selected_hero.get()
        match.fullname = match.name  # Update full name if needed
        # Refresh the image in the original GUI
        new_img = image_map.get(match.name, image_map.get("Default")).copy()
        new_img.thumbnail((128, 128))
        new_photo = ImageTk.PhotoImage(new_img)
        label_widget.configure(image=new_photo)
        label_widget.image = new_photo
        top.destroy()

    tk.Button(top, text="OK", command=submit).pack(pady=(0, 10))

    update_image()
    top.wait_window()  # Block interaction with main window

def show_team_comparison_gui(team1_matches, team2_matches,map):
    global indicator_label
    img2 = None
    cropped = None
    indicator_label = None
    root = tk.Tk()
    null = None
    screen_width = root.winfo_screenwidth()
    x = screen_width // 2
    root.geometry(f"+{x}+0")
    root.withdraw()  # Hide root window
    result = {"blue": [], "red": []}
    resultdict = {"blue": [], "red": []}
    win = tk.Toplevel(root)
    win.geometry(f"+{x}+0")
    
    
    win.title("Team Matchup Comparison")
    win.configure(bg="#1C2026")
    win.attributes("-topmost", True)
    win.grab_set()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    assets_folder = os.path.join(script_dir, "assets_characters")

    image_map = {}
    for filename in os.listdir(assets_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(assets_folder, filename)
            image_map[key] = Image.open(path)  # Store PIL images instead

    # Set layout frame
    main_frame = tk.Frame(win, bg="#1C2026")
    main_frame.pack(padx=10, pady=10)

    # Create team frames (left + center + right)
    left_frame = tk.Frame(main_frame, bg="#2C334B", padx=5, pady=5)
    left_frame.grid(row=0, column=0, sticky="n")
    center_frame = tk.Frame(main_frame, bg="#1C2026", padx=10)
    center_frame.grid(row=0, column=1, sticky="n")
    right_frame = tk.Frame(main_frame, bg="#6B382E", padx=5, pady=5)
    right_frame.grid(row=0, column=2, sticky="n")
    #indicator_label = tk.Label(center_frame, text="", fg="white", bg="#1C2026", font=("Arial", fonts[12]))
    #indicator_label.pack(side="top")
    # Team labels
    tk.Label(left_frame, text="Team 1", font=("Arial", fonts[14], "bold"), fg="white", bg="#2C334B").pack(fill=tk.X)
    tk.Label(right_frame, text="Team 2", font=("Arial", fonts[14], "bold"), fg="white", bg="#6B382E").pack(fill=tk.X)

    # Add player frames for each match
    def add_match_widget(frame, match, bg_color):
        outer = tk.Frame(frame, width=132, height=132, bg=bg_color, highlightthickness=2)
        outer.pack_propagate(False)
        outer.pack(pady=3)
        cropped = None
        img2 = None
        print(match.name)

        # Adjust border color if score > 55
        if match.score >= 55:
            outer.config(highlightbackground="yellow",highlightthickness= 4)
            cropped = match.image
            cropped.thumbnail((128, 128))
            img2 = ImageTk.PhotoImage(cropped)
            
        else:
            outer.config(highlightbackground="black")

        img_obj = get_image_from_map(map, match.name, match.fullname)
        resized = img_obj.copy()
        resized.thumbnail((128, 128))
        img = ImageTk.PhotoImage(resized)
        if cropped:
            resized2 = cropped.copy()
            resized2.thumbnail((128, 128))
            img2 = ImageTk.PhotoImage(resized2)
                
        

        if img:
            label = tk.Label(outer, image=img, bg=bg_color)
            label.image = img  # Prevent garbage collection
        else:
            label = tk.Label(outer, text=match.name, fg="white", bg=bg_color)
        
        label.pack()
        def on_click(event, match=match, label=label, bg=bg_color):
            change_character(match, image_map, label, bg)

        label.bind("<Button-1>", on_click)
        # Hover effect – store a darkened image to use on hover
        def create_overlay(image):
            # Ensure consistent image size and mode
            base = image.copy().convert("RGBA")
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 100))  # semi-transparent black
            combined = Image.alpha_composite(base, overlay)
            return ImageTk.PhotoImage(combined)

        def on_enter(event):
            hero = match.name
            #img_obj = image_map.get(hero, image_map.get("Default"))
            if cropped:
                resized = cropped.copy()
                resized = cropped.resize((128, 128), Image.LANCZOS)
                
            else:
                img_obj = get_image_from_map(map, match.name, match.fullname)
                resized = img_obj.copy()
                resized.thumbnail((128, 128))
            base_img = resized.convert("RGBA")
            overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 100))
            combined = Image.alpha_composite(base_img, overlay)
            hover_img = ImageTk.PhotoImage(combined)

            label.configure(image=hover_img)
            label.image = hover_img
            outer.config(bg="#2a2a2a")

        def on_leave(event):
            hero = match.name
            img_obj = get_image_from_map(map, match.name, match.fullname)
            resized = img_obj.copy()
            resized.thumbnail((128, 128))
            normal_img = ImageTk.PhotoImage(resized)

            label.configure(image=normal_img)
            label.image = normal_img
            outer.config(bg=bg_color)

        def on_click(event, match=match, label=label):
            change_character(match, image_map, label)

        label.bind("<Enter>", on_enter)
        label.bind("<Leave>", on_leave)

    # Populate both teams using iteration and single match
    for match in team1_matches:
        add_match_widget(left_frame, match, "#456093")

    for match in team2_matches:
        add_match_widget(right_frame, match, "#A15444")
    def on_save():
        resultdict["blue"] = [
    {"base_name": m.name, "full_name": m.fullname}
    for m in team1_matches
]
        resultdict["red"] = [
    {"base_name": m.name, "full_name": m.fullname}
    for m in team2_matches
]
        result["blue"] = [m.name for m in team1_matches]
        result["red"] = [m.name for m in team2_matches]
        win.destroy()
    # Save button in center frame
    save_btn = tk.Button(center_frame,fg="white", bg="#3B3B3B",text="Save", command=on_save,font=("Arial", fonts[12],"bold"), width=6,cursor="hand2")
    save_btn.pack(pady=100)
    a = tk.Label(center_frame,bg="#1C2026", text="Click Hero\nto change\nCharacter",fg="white",font=("Arial", fonts[12],"bold"), width=10)
    a.pack(pady=10)
    
    win.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, win.title())
    
    #make_clickthrough()
    
    win.wait_window()  # Block until win is destroyed
    root.destroy()     # Fully close hidden root window
    
    return result["blue"], result["red"], image_map, resultdict["blue"], resultdict["red"]



def create_player_frame(root, player, image_map):
    if player.hero1 not in image_map:
        player.hero1 = "Question"
    if player.hero2 not in image_map:
        player.hero2 = "Question"
    
    outer = tk.Frame(root, width=300, height=400, borderwidth=2, relief="groove")
    outer.pack(side="left", fill="x",padx=0, pady=0)
    outer.pack_propagate(False)

    # Top bar: name + rank icon
    top_bar = tk.Frame(outer, bg="#2b2e41",height=65)
    top_bar.pack(fill="x")
    top_bar.pack_propagate(False)
    
    name_label = tk.Label(top_bar, text=player.name,bg="#2b2e41", fg="white",font=("Calibri", fonts[17], "bold"), anchor="w")
    name_label.pack(side="left", padx=5)
    
    rank_img_raw = image_map.get(player.rank) or image_map.get("Default")
    if rank_img_raw:
        resized = rank_img_raw.copy()
        resized.thumbnail((72,72))  # Resize to 32x32
        rank_img = ImageTk.PhotoImage(resized)
        rank_label = tk.Label(top_bar,bg="#2b2e41", image=rank_img)
        rank_label.image = rank_img  # Prevent garbage collection
        rank_label.pack(side="right", padx=5)

 
    #top_bar.image = rank_img

    # Main content split horizontally
    content = tk.Frame(outer)
    content.pack(fill="both", expand=True)

    # Left (hero images stacked)
    left_frame = tk.Frame(content, bg="#151426",width=150)
    left_frame.pack(side="left", fill="y")
    left_frame.pack_propagate(False)
    
    left_frame_top = tk.Frame(left_frame,bg="#1c1b2d", height=150)
    left_frame_top.pack(side="top", fill="x",pady=5)
    left_frame_top.pack_propagate(False)
    
    hero1_img = image_map.get(player.hero1, image_map.get("Default"))
    resized = hero1_img.copy()
    resized.thumbnail((136,136))
    hero1_img = ImageTk.PhotoImage(resized)
    hero1_label = tk.Label(left_frame_top, bg="#1c1b2d",image=hero1_img)
    hero1_label.pack(pady=5)
    left_frame_top.image1 = hero1_img
    
    left_frame_bot = tk.Frame(left_frame, bg="#1c1b2d",height=150)
    left_frame_bot.pack(side="bottom", fill="x",pady=5)
    left_frame_bot.pack_propagate(False)
    
    

    hero2_img = image_map.get(player.hero2, image_map.get("Default"))
    resized = hero2_img.copy()
    resized.thumbnail((136,136))
    hero2_img = ImageTk.PhotoImage(resized)
    hero2_label = tk.Label(left_frame_bot,bg="#1c1b2d", image=hero2_img)
    hero2_label.pack(pady=5)
    left_frame_bot.image = hero2_img

    # Right (text stacked)
    right_frame = tk.Frame(content, bg="#151426",width=150)
    right_frame.pack(side="right", fill="y")
    right_frame.pack_propagate(False)
    
    right_frame_top = tk.Frame(right_frame, bg="#1c1b2d",height=150)
    right_frame_top.pack(side="top", fill="x",pady=5)
    right_frame_top.pack_propagate(False)
    
    right_frame_bot = tk.Frame(right_frame,bg="#1c1b2d", height=150)
    right_frame_bot.pack(side="bottom", fill="x",pady=5)
    right_frame_bot.pack_propagate(False)
    
    kd1 = "white"
    title = "#BEBFE5"
    
    kd2 = "white"
    dpm1 = "white"
    dpm2 = "white"
    
    if int(float(player.kd1)) >= 3:
        kd1 = "#3ecbff"
    elif int(float(player.kd1))>=2:
        kd1 = "#5de791"
    elif int(float(player.kd1)) <1:
        kd1= "#bf868f"
    if int(float(player.kd2)) >= 3:
        kd2 = "#3ecbff"
    elif int(float(player.kd2)) >=2:
        kd2 = "#5de791"
    elif int(float(player.kd2)) <1:
        kd2= "#bf868f"

    if int(float(player.dpm1)) >= 1500:
        dpm1 = "#3ecbff"
    elif int(float(player.dpm1))>=1100:
        dpm1 = "#5de791"
    elif int(float(player.dpm1)) <750:
        dpm1= "#bf868f"
    if int(float(player.dpm2)) >= 1500:
        dpm2 = "#3ecbff"
    elif int(float(player.dpm2)) >=1100:
        dpm2 = "#5de791"
    elif int(float(player.dpm2)) <750:
        dpm2= "#bf868f"


    latitle= tk.Label(right_frame_top, text=f"\nKD",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11], "bold"))
    latitle.pack(pady=0)
    la= tk.Label(right_frame_top, text=f"{player.kd1}\n",fg=kd1,bg="#1c1b2d", font=("Calibri", fonts[13],"bold"))
    la.pack(pady=0)
    la2title= tk.Label(right_frame_top, text=f"{player.string1}",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
    la2title.pack(pady=0)
    la2= tk.Label(right_frame_top, text=f"{player.dpm1}",fg=dpm1,bg="#1c1b2d", font=("Calibri", fonts[13],"bold"))
    la2.pack(pady=0)
   # tk.Label(right_frame, text="Placeholder 1", font=("Calibri", fonts[4])).pack(pady=5)
    #tk.Label(right_frame, text="Placeholder 2", font=("Calibri", fonts[4])).pack(pady=5)
    lbtitle= tk.Label(right_frame_bot, text=f"\nKD",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
    lbtitle.pack(pady=0)
    lb = tk.Label(right_frame_bot, text=f"{player.kd2}\n",fg=kd2,bg="#1c1b2d", font=("Calibri", fonts[13],"bold"))
    lb.pack(pady=0)
    lb2title= tk.Label(right_frame_bot, text=f"{player.string2}",fg=title,bg="#1c1b2d", font=("Calibri", fonts[11],"bold"))
    lb2title.pack(pady=0)
    lb2= tk.Label(right_frame_bot, text=f"{player.dpm2}",fg=dpm2,bg="#1c1b2d", font=("Calibri", fonts[13],"bold"))
    lb2.pack(pady=0)
    #tk.Label(right_frame, text="Placeholder 3", font=("Calibri", fonts[4])).pack(pady=5)
    #tk.Label(right_frame, text="Placeholder 4", font=("Calibri", fonts[4])).pack(pady=5)
    
    

    return outer

def show_gui(players):
    global indicator_label
    root = tk.Tk()
    root.title("Match Overview")
    width = len(players) * 300
    screen_width = root.winfo_screenwidth()
    x = (screen_width - width) // 2
    y = 0
    root.geometry(f"{width}x400+{x}+{y}")

    root.configure(bg="black")
    root.overrideredirect(True)
    root.attributes("-topmost", True)  # Always on top
    script_dir = os.path.dirname(os.path.abspath(__file__))

    assets_folder = os.path.join(script_dir, "assets")

    image_map = {}
    for filename in os.listdir(assets_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(assets_folder, filename)
            image_map[key] = Image.open(path)  # Store PIL images instead

    title_bar = tk.Frame(root, bg="#141420", relief="groove", height=30)
    title_bar.pack(fill="x", side="top")
    title_bar.pack_propagate(False)
    
    close_btn = tk.Button(title_bar, command=lambda: close(root,script_dir),text="X", width=2,height=1,fg="white", relief="flat",bg="#141420", font=("Lucida Console", fonts[16]), cursor="hand2")
    close_btn.pack(side="right", padx=0)
    hide_btn = tk.Button(title_bar, command=lambda: toggle_transparency(root,hide_btn),text="Hide", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[14]), cursor="hand2")
    hide_btn.pack(side="right", padx=10)
    global lock
    lock = tk.Button(title_bar, command=toggle_clickthrough,text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[8]), cursor="hand2")
    lock.pack(side="right", padx=10)
    indicator_label = tk.Label(title_bar, text="", fg="white", bg="#141420", font=("Arial", fonts[12]))
    indicator_label.pack(side="left",padx=0)

    close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#d41c1c"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#141420"))


    hide_btn.bind("<Enter>", lambda e: hide_btn.config(bg="#31314D"))
    hide_btn.bind("<Leave>", lambda e: hide_btn.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    
    
    for player in players:
        create_player_frame(root, player, image_map)

    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()

    root.mainloop()
def toggle_transparency(root,btn):
    if hasattr(root, "_is_transparent") and root._is_transparent:
        # Restore to opaque
        btn.config(text="Hide")
        root.attributes("-alpha", 1.0)
        root._is_transparent = False
    else:
        # Set to transparent
        btn.config(text="Show")
        root.attributes("-alpha", 0.25)  # You can adjust this value (0.0 to 1.0)
        root._is_transparent = True


    

def close(root,script_dir):
    debug_path = os.path.join(script_dir, "debug")
    debug_img = os.path.join(debug_path, "Last Banner.png")
    root.update()  # Make sure geometry info is up-to-date
    x = root.winfo_rootx()
    y = root.winfo_rooty()
    w = x + root.winfo_width()
    h = y + root.winfo_height()

    # Capture region and save
    img = ImageGrab.grab(bbox=(x, y, w, h))
    img.save(debug_img)
    print(f"Saved screenshot to {debug_img}")
    root.destroy()
    
    #main3()

def close2(root):
    root.destroy()
    sys.exit(0)

def close3(root):
    root.destroy()

def show_launcher(on_trigger,on_match):
    global bhidden, bdebug_menu, indicator_label,main, var2, var1, trigger_func,trigger2_func,root,cb1,cb2,cb3
    global fonts
    
    font_scale = 1
    print(config.mobile_mode)
    if config.mobile_mode:
        font_scale = 1
        print(font_scale)
    font_sizes = list(range(6, 70))
    fonts = {size: scale_font(font_scale, size) for size in font_sizes}
    bhidden = False
    bdebug_menu = False
    root = tk.Tk()
    root.title("Capture Names")
    screen_width = root.winfo_screenwidth()
    x = (screen_width // 2)-50
    y = 0
    root.geometry(f"+{x}+{y}")
    root.attributes("-topmost", True)
    root.configure(bg="#151426")
    root.overrideredirect(True)
    title_bar2 = tk.Frame(root, bg="#141420", relief="solid", width=250,height=17)
    title_bar2.pack(fill="x", side="top",ipady=3)
    title_bar2.pack_propagate(False)
    main = tk.Frame(root, bg="#151426", relief="solid", height=30, width=250)
    main.pack(fill="x", padx=10,pady=5, side="bottom")
    deb = tk.Frame(root, bg="#151426", relief="solid", height=30, width=250)
    lef = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
    rig = tk.Frame(deb, bg="#151426", relief="solid", height=30, width=125)
    lef.pack(fill="x", padx=0,pady=0, side="left")
    rig.pack(fill="x", padx=0,pady=0, side="right")
    var1 = tk.BooleanVar()
    var2 = tk.BooleanVar()
    var3 = tk.BooleanVar()
    var4 = tk.BooleanVar()
    global global_random_ban, global_random_matchup, global_dex, global_debugmode, global_debugflag
    global_debugmode = config.debug_mode
    var1.set(global_random_ban)
    var2.set(global_random_matchup)
    var3.set(global_dex)
    var4.set(global_debugmode)
    # Variables to hold checkbox states
    
    #if config.randomize_ban:
        #var1.set(True)
    #f config.randomize_matchup:
        #var2.set(True)

    # Create checkboxes on the 'deb' frame
    frame = lef
    global_debugflag = False
    if config.debug_mode:
        frame = rig
        cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=("Calibri", fonts[10]),variable=var1)
        cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2,font=("Calibri", fonts[10]))
        cb1.pack(anchor="w",padx=0)
        cb2.pack(anchor="w",padx=0)
        global_debugflag = True

    
    cb3 = tk.Checkbutton(frame, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
    cb4 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Enable Debug", variable=var4,font=("Calibri", fonts[10]))
    #cb3 = tk.Checkbutton(deb, text="Option 3", variable=var3)

    # Pack them onto the frame
    
    cb3.pack(anchor="w",padx=0)
    cb4.pack(anchor="w",padx=0)
    #cb3.pack(anchor="w")
    def toggle_hide():
        global bhidden, bdebug_menu
        bhidden = not bhidden
        if bhidden:
            if bdebug_menu:
                deb.pack_forget()
            else:
                main.pack_forget()
            hide_btn2.config(text="Show")
            
        else:
            if bdebug_menu:
                deb.pack(fill="x", padx=0,pady=6, side="bottom")
            else:
                main.pack(fill="x", padx=10,pady=5, side="bottom")
            
            hide_btn2.config(text="Hide")
        root.update_idletasks()
        root.geometry("")
    def toggle_debug():
        import config
        global bdebug_menu,bhidden,global_random_matchup,global_random_ban,global_dex,global_debugmode,global_debugflag,cb1,cb2,cb3
        bdebug_menu = not bdebug_menu
        if bhidden:
            bhidden = False
            hide_btn2.config(text="Hide")
        if bdebug_menu:
            
            main.pack_forget()
            debug.config(text="Back")
            
            global_dex = var3.get()
            config.dex = global_dex
            global_debugmode = var4.get()
            config.debug_mode = global_debugmode
            if config.debug_mode:
                if not global_debugflag:

                    cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=("Calibri", fonts[10]),variable=var1)
                    cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2,font=("Calibri", fonts[10]))
                    cb1.pack(anchor="w",padx=0)
                    cb2.pack(anchor="w",padx=0)
                    global_debugflag = True
                    cb3.destroy()
                    cb3 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                    cb3.pack(anchor="w",padx=0)
                global_random_ban = var1.get()
                global_random_matchup = var2.get()
                config.randomize_ban = global_random_ban
                config.randomize_matchup = global_random_matchup
            elif not config.debug_mode and global_debugflag:
                cb1.destroy()
                cb2.destroy()
                cb3.destroy()
                cb3 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                cb3.pack(anchor="w",padx=0)
                global_debugflag = False
            print(f"Dexerto: {config.dex}")
            deb.pack(fill="x", padx=0,pady=6, side="bottom")
            
        else:
            global_dex = var3.get()
            config.dex = global_dex
            global_debugmode = var4.get()
            config.debug_mode = global_debugmode
            if config.debug_mode:
                if not global_debugflag:
                    cb1 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Bans", font=("Calibri", fonts[10]),variable=var1)
                    cb2 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Random Matchup", variable=var2,font=("Calibri", fonts[10]))
                    cb1.pack(anchor="w",padx=0)
                    cb2.pack(anchor="w",padx=0)
                    global_debugflag = True
                    cb3.destroy()
                    cb3 = tk.Checkbutton(rig, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                    cb3.pack(anchor="w",padx=0)
                global_random_ban = var1.get()
                global_random_matchup = var2.get()
                config.randomize_ban = global_random_ban
                config.randomize_matchup = global_random_matchup
            elif not config.debug_mode and global_debugflag:
                cb1.destroy()
                cb2.destroy()
                cb3.destroy()
                cb3 = tk.Checkbutton(lef, bg="#151426",fg="white",selectcolor="#151426",text="Use Classic Logic", variable=var3,font=("Calibri", fonts[10]))
                cb3.pack(anchor="w",padx=0)
                global_debugflag = False
            print(f"Dexerto: {config.dex}")
            deb.pack_forget()
            debug.config(text="Debug")
            main.pack(fill="x", padx=10,pady=5, side="bottom")

    close_btn2 = tk.Button(title_bar2, command=lambda: close2(root),text="X", width=2,height=1,fg="white", relief="flat",bg="#141420", font=("Lucida Console", fonts[11]), cursor="hand2")
    close_btn2.pack(side="right", padx=0)
    hide_btn2 = tk.Button(title_bar2, command=toggle_hide,text="Hide", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[10]), cursor="hand2")
    hide_btn2.pack(side="right", padx=3)
    
    if config.debug_mode or config.debug_menu:
        debug = tk.Button(title_bar2, command=toggle_debug,text="Debug", relief="flat",fg="#FCD92E", bg="#141420", font=("Lucida Console", fonts[10]), cursor="hand2")
        debug.pack(side="right", padx=3)
        debug.bind("<Enter>", lambda e: debug.config(bg="#31314D"))
        debug.bind("<Leave>", lambda e: debug.config(bg="#141420"))
    global lock
    lock = tk.Button(title_bar2, command=toggle_clickthrough,text="Lock(F6)", relief="flat",fg="white", bg="#141420", font=("Lucida Console", fonts[8]), cursor="hand2")
    lock.pack(side="right", padx=3)
    indicator_label = tk.Label(title_bar2, text="", fg="white", bg="#141420", font=("Arial", fonts[12]))
    indicator_label.pack(side="left",padx=0)
    close_btn2.bind("<Enter>", lambda e: close_btn2.config(bg="#d41c1c"))
    close_btn2.bind("<Leave>", lambda e: close_btn2.config(bg="#141420"))

    hide_btn2.bind("<Enter>", lambda e: hide_btn2.config(bg="#31314D"))
    hide_btn2.bind("<Leave>", lambda e: hide_btn2.config(bg="#141420"))
    lock.bind("<Enter>", lambda e: lock.config(bg="#31314D"))
    lock.bind("<Leave>", lambda e: lock.config(bg="#141420"))
    


    button = tk.Button(main,text="Bans (F8)", height=1, relief="flat", bg="#FCD92E",font=("Calibri", fonts[12], "bold"),command=lambda: trigger1(var1.get()), cursor="hand2")
    button.pack(side="left",padx=11)
    button.bind("<Enter>", lambda e: button.config(bg="#A18D25"))
    button.bind("<Leave>", lambda e: button.config(bg="#FCD92E"))
    button1 = tk.Button(main,text="Counters (F10)",height=1, relief="flat", bg="#FCD92E",font=("Calibri", fonts[12], "bold"),command=lambda: trigger22(var2.get()), cursor="hand2")
    button1.pack(side="right",padx=11)
    button1.bind("<Enter>", lambda e: button1.config(bg="#A18D25"))
    button1.bind("<Leave>", lambda e: button1.config(bg="#FCD92E"))

    after_id = None  # Store enforce loop
    


    # def force_focus():
    #     try:
    #         root.lift()
    #         root.focus_force()
    #         root.attributes('-topmost', True)
    #     except:
    #         pass
    #     nonlocal after_id
    #     after_id = root.after(1000, force_focus)

    def trigger(flag):
        if flag:
            config.randomize_ban = True
        if after_id:
            root.after_cancel(after_id)
        #root.destroy()
        on_trigger()

    def trigger1(flag):
        if flag:
            config.randomize_ban = True
        if after_id:
            root.after_cancel(after_id)
        root.destroy()
        on_trigger()

    def trigger2(flag):
        if flag:
            config.randomize_matchup = True
        if after_id:
            root.after_cancel(after_id)
        #root.destroy()
        on_match()
    def trigger22(flag):
        if flag:
            config.randomize_matchup = True
        if after_id:
            root.after_cancel(after_id)
        root.destroy()
        on_match()
    root.update_idletasks()
    global hwnd
    if not config.mobile_mode:
        hwnd = win32gui.FindWindow(None, root.title())
    #make_clickthrough()
    trigger2_func = trigger2
    trigger_func = trigger

    root.mainloop()


if not config.mobile_mode:
    import threading
    def start_hotkey_listener():
        keyboard.add_hotkey('f6', toggle_clickthrough)
        keyboard.wait()  # Keeps the listener alive

    listener_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    listener_thread.start()
    keyboard.add_hotkey('f8', handle_f8)

    keyboard.add_hotkey('f10', handle_f10)