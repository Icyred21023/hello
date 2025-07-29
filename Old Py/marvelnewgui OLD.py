import tkinter as tk
from PIL import ImageTk, Image
import re
import os

class Player:
    def __init__(self, name, data):
        self.hero1 = data["hero1"]
        self.kd1 = data["kd1"]
        self.hero2 = data["hero2"]
        self.kd2 = data["kd2"]
        self.rank = data["rank"]
        self.name = name

    def strip_rank_tier(self, rank_str):
        return re.sub(r'\s+(I{1,3}|IV|V)$', '', rank_str)

    def sort_by_time(self, data):
        segments = data["data"]
        hero_segments = [segment for segment in segments if segment.get("type") == "hero"]
        sorted_heroes = sorted(hero_segments, key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        return sorted_heroes

    def __repr__(self):
        return f"Player(name={self.name}, rank={self.rank})"

def create_player_frame(root, player, image_map):
    outer = tk.Frame(root, width=300, height=400, borderwidth=2, relief="groove")
    outer.pack(side="left", padx=5, pady=5)
    outer.pack_propagate(False)

    # Top bar: name + rank icon
    top_bar = tk.Frame(outer, bg="#2b2e41",height=65)
    top_bar.pack(fill="x")
    top_bar.pack_propagate(False)
    
    name_label = tk.Label(top_bar, text=player.name,bg="#2b2e41", fg="white",font=("Arial", 4, "bold"), anchor="w")
    name_label.pack(side="left", padx=5)
    
    rank_img_raw = image_map.get(player.rank) or image_map.get("Default")
    if rank_img_raw:
        resized = rank_img_raw.copy()
        resized.thumbnail((64,64))  # Resize to 32x32
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
    hero1_img = ImageTk.PhotoImage(hero1_img)
    hero1_label = tk.Label(left_frame_top, bg="#1c1b2d",image=hero1_img)
    hero1_label.pack(pady=5)
    left_frame_top.image1 = hero1_img
    
    left_frame_bot = tk.Frame(left_frame, bg="#1c1b2d",height=150)
    left_frame_bot.pack(side="bottom", fill="x",pady=5)
    left_frame_bot.pack_propagate(False)
    
    

    hero2_img = image_map.get(player.hero2, image_map.get("Default"))
    hero2_img = ImageTk.PhotoImage(hero2_img)
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
    
    kd2 = "white"
    
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
    
    

    la= tk.Label(right_frame_top, text=f"KD: {player.kd1}",fg=kd1,bg="#1c1b2d", font=("Arial", 3))
    la.pack(pady=5)
   # tk.Label(right_frame, text="Placeholder 1", font=("Arial", 4)).pack(pady=5)
    #tk.Label(right_frame, text="Placeholder 2", font=("Arial", 4)).pack(pady=5)

    lb = tk.Label(right_frame_bot, text=f"KD: {player.kd2}",fg=kd2,bg="#1c1b2d", font=("Arial", 3))
    lb.pack(pady=5)
    #tk.Label(right_frame, text="Placeholder 3", font=("Arial", 4)).pack(pady=5)
    #tk.Label(right_frame, text="Placeholder 4", font=("Arial", 4)).pack(pady=5)
    
    

    return outer

def show_gui(players):
    root = tk.Tk()
    root.title("Match Overview")
    root.geometry("1200x400")
    root.configure(bg="black")

    assets_folder = "/storage/emulated/0/assets"

    image_map = {}
    for filename in os.listdir(assets_folder):
        if filename.lower().endswith(".png"):
            key = os.path.splitext(filename)[0]
            path = os.path.join(assets_folder, filename)
            image_map[key] = Image.open(path)  # Store PIL images instead


    for player in players:
        create_player_frame(root, player, image_map)

    root.mainloop()

# Setup
json = {
"hero1":"Hawkeye",
"hero2": "Ultron",
"kd1": "2.21",
"kd2": "0.24",
"rank": "Diamond"
}

json2 = {
"hero1":"Thor",
"hero2": "Bruce Banner",
"kd1": "6.43",
"kd2": "1.24",
"rank": "One Above All"
}

json3 = {
"hero1":"Magik",
"hero2": "Rocket Raccoon",
"kd1": "2.89",
"kd2": "3.4",
"rank": "Platinum"
}

json4 = {
"hero1":"Iron Man",
"hero2": "Ultron",
"kd1": "4.24",
"kd2": "3.15",
"rank": "Grandmaster"
}

json5 = {
"hero1":"The Thing",
"hero2": "Invisible Woman",
"kd1": "2.63",
"kd2": "1.62",
"rank": "Gold"
}

json6 = {
"hero1":"Hela",
"hero2": "Namor",
"kd1": "5.17",
"kd2": "4.95",
"rank": "Celestial"
}

players = [
    Player("ProfChloroform", json),
    Player("Biczilla", json2),
    Player("SexSlave", json3),
    Player("MickeyMouse", json4),
    Player("STDMagnet", json5),
    Player("AnimalFever", json6)
]

show_gui(players)
