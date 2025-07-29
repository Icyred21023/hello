import re, json, requests

url = "https://www.peakrivals.com"
html = requests.get(url).text
print(html)
# Use re.DOTALL so it captures multiline JSON
match = re.search(r'window\.__INITIAL_DATA__\s*=\s*(\{.*?\});', html, re.DOTALL)

if match:
    data = json.loads(match.group(1))
    counters = data["hero"]["counters"]
    print(json.dumps(counters, indent=2))
else:
    print("Failed to find hero data.")
