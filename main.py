import datetime
import json
import os
import re
import urllib.request

# =========================================================================
# ১. গিটহাব সিক্রেট (GitHub Secret) থেকে কাস্টম সোর্স লোড করা
# =========================================================================
DEFAULT_LOGO = (
    "https://github.com/ahmedstore75/iptv-auto/blob/main/image.png"
)
CATEGORY_ORDER = ["Bangla", "Sports", "Hindi", "English", "Movies", "India"]

# গিটহাব অ্যাকশন থেকে MY_CUSTOM_SOURCES সিক্রেট রিড করবে
sources_json = os.environ.get("MY_CUSTOM_SOURCES")

if not sources_json:
    print("Error: MY_CUSTOM_SOURCES secret is not set!")
    exit(1)

try:
    MY_CUSTOM_SOURCES = json.loads(sources_json)
except Exception as e:
    print(f"Error parsing JSON from secret: {e}")
    exit(1)


def get_clean_url(url):
    """ইউআরএল ট্রিম করে পিওর স্ট্রিম লিঙ্ক বের করা"""
    return url.strip().split("?")[0].rstrip("/").lower()


all_channels = []
seen_m3u8_urls = set()  # ইউনিক .m3u8 লিঙ্ক ট্র্যাক রাখার জন্য

print("Processing sources... Ensuring unique links.")

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for source in MY_CUSTOM_SOURCES:
    category_name = source.get("category", "Other")
    src_url = source.get("url", "")

    if not src_url:
        continue

    try:
        req = urllib.request.Request(src_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="ignore")

            lines = content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    metadata = line
                    if i + 1 < len(lines):
                        stream_url = lines[i + 1].strip()
                        clean_url = get_clean_url(stream_url)

                        # লিঙ্ক চেক এবং ডুপ্লিকেট ফিল্টারিং
                        if stream_url.startswith("http") and ".m3u8" in clean_url:
                            if clean_url not in seen_m3u8_urls:
                                seen_m3u8_urls.add(clean_url)

                                # ক্যাটাগরি সেট
                                if (
                                    'group-title="' not in metadata
                                    or 'group-title=""' in metadata
                                ):
                                    metadata = metadata.replace(
                                        "#EXTINF:-1",
                                        f'#EXTINF:-1 group-title="{category_name}"',
                                    )

                                # লোগো সেট
                                if 'tvg-logo=""' in metadata:
                                    metadata = metadata.replace(
                                        'tvg-logo=""',
                                        f'tvg-logo="{DEFAULT_LOGO}"',
                                    )
                                elif 'tvg-logo="' not in metadata:
                                    metadata = metadata.replace(
                                        "#EXTINF:-1",
                                        f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}"',
                                    )

                                all_channels.append(
                                    (category_name, metadata, stream_url)
                                )
                        i += 1
                i += 1
    except Exception as e:
        print(f"Error reading source: {e}")


# ক্যাটাগরি অর্ডারে সাজানো
def sort_key(item):
    category = item[0]
    return (
        CATEGORY_ORDER.index(category)
        if category in CATEGORY_ORDER
        else len(CATEGORY_ORDER)
    )


all_channels.sort(key=sort_key)

# =========================================================================
# ২. M3U ও JSON ফাইল জেনারেট করা
# =========================================================================
bd_time = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
formatted_time = bd_time.strftime("%Y-%m-%d %H:%M:%S")
total_channels = len(all_channels)

m3u_output = f"""#EXTM3U
#=================================
# 🖥️ Developed by: Ahammad Ali
# 🔗 Telegram: https://t.me/banglatvlivefree
# 🕒 Last Updated: {formatted_time} (BD Time)
# 📺 Channels Count: {total_channels}
# 🔒 Usage: Personal / Educational
#=================================

"""

json_playlist = []

for category, metadata, stream_url in all_channels:
    m3u_output += f"{metadata}\n{stream_url}\n"

    logo_match = re.search(r'tvg-logo="([^"]*)"', metadata)
    logo = logo_match.group(1) if logo_match else DEFAULT_LOGO

    group_match = re.search(r'group-title="([^"]*)"', metadata)
    group = group_match.group(1) if group_match else category

    name_split = metadata.split(",")
    name = name_split[-1].strip() if len(name_split) > 1 else "Unknown"

    json_playlist.append(
        {"name": name, "logo": logo, "group": group, "url": stream_url}
    )

with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_output)

with open("channels.json", "w", encoding="utf-8") as f:
    json.dump(json_playlist, f, indent=4, ensure_ascii=False)

print(f"Done! Updated playlist.m3u and channels.json with {total_channels} channels.")
