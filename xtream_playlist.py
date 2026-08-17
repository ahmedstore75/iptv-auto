import re
import urllib.request
import time
from datetime import datetime, timezone, timedelta

# --- CONFIG ---
BASE_URL = "http://filex.me:8080"
USERNAME = "3114654477"
PASSWORD = "5787654467"

# Xtream Codes M3U Download URL
M3U_SOURCE_URL = f"{BASE_URL}/get.php?username={USERNAME}&password={PASSWORD}&type=m3u_plus&output=m3u8"

# ক্লাউডফ্লেয়ার ওয়ার্কারের ডোমেইন URL
WORKER_DOMAIN = "https://saiptvlive.ahmed-bd-org.workers.dev"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_playlist_content(url, retries=3, delay=5, timeout=60):
    for attempt in range(1, retries + 1):
        try:
            print(f"🔄 Attempt {attempt}/{retries}: Downloading playlist from Xtream server...")
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"⏳ Waiting {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                raise e

def filter_live_channels(content):
    """কেবলমাত্র লাইভ চ্যানেল ফিল্টার করে ফাইল সাইজ ১০০ MB এর নিচে রাখার জন্য"""
    lines = content.splitlines()
    filtered_lines = ["#EXTM3U"]
    
    current_extinf = ""
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif not line_str.startswith("#") and current_extinf:
            # VOD/Movie/Series বাদ দিয়ে কেবল Live লিঙ্ক যুক্ত করা
            if "/movie/" not in line_str and "/series/" not in line_str:
                filtered_lines.append(current_extinf)
                filtered_lines.append(line_str)
            current_extinf = ""
            
    return "\n".join(filtered_lines)

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)

        # ১. লাইভ টিভি চ্যানেল ফিল্টার
        live_content = filter_live_channels(content)

        # ২. ক্লাউডফ্লেয়ার ওয়ার্কার লিঙ্ক দিয়ে রিপ্লেস করা
        pattern = re.compile(
            rf"{re.escape(BASE_URL)}/(?:live/)?{re.escape(USERNAME)}/{re.escape(PASSWORD)}/([0-9]+)(\.m3u8|\.ts)?"
        )
        
        def replace_url(match):
            stream_id = match.group(1)
            ext = match.group(2) if match.group(2) else ".m3u8"
            return f"{WORKER_DOMAIN}/{stream_id}{ext}"

        updated_m3u = pattern.sub(replace_url, live_content)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        header_comment = f"# 📦 Playlist X (Live TV)\n# ⏰ BD Updated time: {bd_time}\n"
        updated_m3u = updated_m3u.replace("#EXTM3U", f"#EXTM3U\n{header_comment}", 1)

        # সরাসরি playlist_x.m3u ফাইলে সেভ করা
        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(updated_m3u)

        print(f"✅ playlist_x.m3u generated successfully at {bd_time}")

    except Exception as e:
        print(f"❌ Error fetching playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
