import os
import json
from collections import Counter

script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, "matchup.json")
save = os.path.join(script_dir,"editmatchup.json")
with open(save, "r") as f:
    data = json.load(f)
red = ["Venom", "Peni Parker", "Hawkeye", "Black Panther", "Luna Snow", "Loki"]
stored_list = []
combined_list =[]
for item in red:
    counert = data[item]["counterPicks"]
    for items in counert:
        char = items["name"]
        print(f"Name: {char}")
        stored_list.append(char)
        
# Example lists
print(stored_list)

# Combine all lists into one
#combined = list1 + list2 + list3

# Count the occurrences of each string
counts = Counter(stored_list)
negative_list = []
for item in counts:
    counert = data[item]["counterPicks"]
    for items in counert:
        char = items["name"]
        if char in red:
            negative_list.append(item)
negative_count = Counter(negative_list)
negative_count = Counter({k: -v for k, v in negative_count.items()})
print(negative_count)
result = negative_count + counts
all_keys = set(counts) | set(negative_count)
combined = {k: counts.get(k, 0) + negative_count.get(k, 0) for k in all_keys}

sorted_results = result.most_common()
sorted_counts = counts.most_common()
sorted_negative = negative_count.most_common()
print("/n")
for item in sorted_counts:
    print(f"Positive Print: {item}")
print("/n")
for item in sorted_negative:
    print(f"Negative Print: {item}")
print("/n")
for item in sorted_results:
    print(f"Combined Print: {item}")
print(combined)
# Print results
#print(counts)
sorted_counts = counts.most_common()
for item in sorted_counts:
    name, count = item
    #print(f"Printout:{name}")
