import datetime
import json
import os
import re
import urllib.request

# =========================================================================
# ১. গিটহাব সিক্রেট (GitHub Secret) থেকে কাস্টম সোর্স লোড করা
# =========================================================================
DEFAULT_LOGO = "https://github.com/ahmedstore75/iptv-auto/blob/main/image.png"
CATEGORY_ORDER = ["Bangla", "Sports", "Hindi", "English", "Movies", "India"]

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
    """ইউআরএল ট্রিম করা"""
    return url.strip().split("?")[0].rstrip("/").lower()

all_channels = []
seen_urls = set()  # ইউনিক লিঙ্ক ট্র্যাক রাখার জন্য

print("Processing sources... Ensuring unique links.")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for source in MY_CUSTOM_SOURCES:
    category_name = source.get("category", "Other")
    src_url = source.get("url", "")

    if not src_url:
        continue

    try:
        req = urllib.request.Request(src_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            content_bytes = response.read()
            content = content_bytes.decode("utf-8", errors="ignore")

            # চেক করা ডাটাটি JSON নাকি M3U
            is_json = False
            try:
                json_data = json.loads(content)
                is_json = True
            except Exception:
                is_json = False

            if is_json:
                # --- JSON API পার্সিং লজিক ---
                categories = json_data.get("categories", [])
                for cat in categories:
                    cat_title = cat.get("name", category_name)
                    channels = cat.get("channels", [])
                    for ch in channels:
                        ch_name = ch.get("name", "Unknown")
                        ch_logo = ch.get("logo", DEFAULT_LOGO)
                        stream_url = ch.get("stream_url", "").strip()
                        clean_url = get_clean_url(stream_url)

                        # শুধু http/https দিয়ে শুরু হলেই অ্যালাউ করবে (m3u8 বাধ্যতামূলক নয়)
                        if stream_url.startswith("http"):
                            if clean_url not in seen_urls:
                                seen_urls.add(clean_url)
                                metadata = f'#EXTINF:-1 tvg-logo="{ch_logo}" group-title="{cat_title}",{ch_name}'
                                all_channels.append((cat_title, metadata, stream_url))
            else:
                # --- M3U / Text পার্সিং লজিক ---
                lines = content.splitlines()
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith("#EXTINF"):
                        metadata = line
                        if i + 1 < len(lines):
                            stream_url = lines[i + 1].strip()
                            clean_url = get_clean_url(stream_url)

                            # শুধু http/https দিয়ে শুরু হলেই অ্যালাউ করবে (m3u8 বাধ্যতামূলক নয়)
                            if stream_url.startswith("http"):
                                if clean_url not in seen_urls:
                                    seen_urls.add(clean_url)

                                    if 'group-title="' not in metadata or 'group-title=""' in metadata:
                                        metadata = metadata.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{category_name}"')

                                    if 'tvg-logo=""' in metadata:
                                        metadata = metadata.replace('tvg-logo=""', f'tvg-logo="{DEFAULT_LOGO}"')
                                    elif 'tvg-logo="' not in metadata:
                                        metadata = metadata.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}"')

                                    all_channels.append((category_name, metadata, stream_url))
                            i += 1
                    i += 1
    except Exception as e:
        print(f"Error reading source ({src_url}): {e}")

# ক্যাটাগরি অর্ডারে সাজানো
def sort_key(item):
    category = item[0]
    return CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)

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

    json_playlist.append({
        "name": name,
        "logo": logo,
        "group": group,
        "url": stream_url
    })

with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_output)

with open("channels.json", "w", encoding="utf-8") as f:
    json.dump(json_playlist, f, indent=4, ensure_ascii=False)

print(f"Done! Updated playlist.m3u and channels.json with {total_channels} channels.")
