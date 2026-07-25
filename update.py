import requests

with open("sources.txt", "r", encoding="utf-8") as f:
    sources = [line.strip() for line in f if line.strip()]

output = "#EXTM3U\n"
seen = set()

for url in sources:
    try:
        print("Loading:", url)
        text = requests.get(url, timeout=30).text
        lines = text.splitlines()

        i = 0
        while i < len(lines):
            if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
                info = lines[i]
                link = lines[i + 1]

                if link.startswith("http") and link not in seen:
                    seen.add(link)
                    output += info + "\n"
                    output += link + "\n"

                i += 2
            else:
                i += 1

    except Exception as e:
        print("Error:", e)

with open("StreamLinks-BD.m3u", "w", encoding="utf-8") as f:
    f.write(output)

print("Done!")
