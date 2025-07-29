from PIL import Image, ImageTk
import os

# Global dictionary to store all image assets
image_map = {
    "Bronze": ImageTk.PhotoImage(Image.open("assets/Bronze.png")),
    "Silver": ImageTk.PhotoImage(Image.open("assets/Silver.png")),
    "Gold": ImageTk.PhotoImage(Image.open("assets/Gold.png")),
    "Platinum": ImageTk.PhotoImage(Image.open("assets/Platinum.png")),
    "Diamond": ImageTk.PhotoImage(Image.open("assets/Diamond.png")),
    "Grandmaster": ImageTk.PhotoImage(Image.open("assets/Grandmaster.png")),
    "Celestial": ImageTk.PhotoImage(Image.open("assets/Celestial.png")),
    "Eternity": ImageTk.PhotoImage(Image.open("assets/Eternity.png")),
    "One Above All": ImageTk.PhotoImage(Image.open("assets/One Above All.png")),
    # add more as needed
}