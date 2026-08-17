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

# Regex ফিল্টারিং প্যাটার্ন
BD_PATTERN = re.compile(r'(?i)\b(BD|BANGLADESH|BANGLA)\b')
IN_PATTERN = re.compile(r'(?i)\b(IN|INDIA|INDIAN)\b')
IN_GENRE_PATTERN = re.compile(r'(?i)(MOVIE|MOVIES|CINEMA|FILM|MUSIC|GANA|SONG|SPORT|SPORTS|CRICKET|FOOTBALL)')
SPORTS_PATTERN = re.compile(r'(?i)(SPORT|SPORTS|CRICKET|FOOTBALL|SOCCER|T20|IPL|BEIN|ESPN|SUPERSPORT|WILLOW|TEN\s*SPORTS|STAR\s*SPORTS|SONY\s*SPORTS|SKY\s*SPORTS|FOX\s*SPORTS|CANAL\+\s*SPORT|ASTRO|EUROSPORT|DAZN|WWE|RACING|GOLF|TENNIS)')

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

def filter_requested_channels(content):
    lines = content.splitlines()
    filtered_lines = ["#EXTM3U"]
    
    current_extinf = ""
    added_count = 0
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif not line_str.startswith("#") and current_extinf:
            is_vod = "/movie/" in line_str or "/series/" in line_str
            
            if not is_vod:
                is_bd = bool(BD_PATTERN.search(current_extinf))
                is_india_targeted = bool(IN_PATTERN.search(current_extinf)) and bool(IN_GENRE_PATTERN.search(current_extinf))
                is_sports = bool(SPORTS_PATTERN.search(current_extinf))
                
                if is_bd or is_india_targeted or is_sports:
                    filtered_lines.append(current_extinf)
                    filtered_lines.append(line_str)
                    added_count += 1
                
            current_extinf = ""
            
    print(f"📊 Total {added_count} custom channels filtered.")
    return "\n".join(filtered_lines)

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)

        # ১. ফিল্টারিং প্রয়োগ
        filtered_content = filter_requested_channels(content)

        # ২. ডাইনামিক হ্যাশ/টোকেন সহ যেকোনো লিঙ্ক রূপান্তর: WORKER_DOMAIN/<token>/index.m3u8
        pattern = re.compile(rf"{re.escape(BASE_URL)}/([^\s\n\r]+)")
        
        def replace_url(match):
            stream_path = match.group(1).rstrip('/')
            # এক্সটেনশন থাকলে তা ক্লিন করে শেষে /index.m3u8 যোগ করা
            clean_path = re.sub(r'(\.m3u8|\.ts)$', '', stream_path)
            return f"{WORKER_DOMAIN}/{clean_path}/index.m3u8"

        updated_m3u = pattern.sub(replace_url, filtered_content)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        header_comment = f"# 📦 Custom Filtered Playlist X\n# ⏰ BD Updated time: {bd_time}\n"
        updated_m3u = updated_m3u.replace("#EXTM3U", f"#EXTM3U\n{header_comment}", 1)

        # playlist_x.m3u ফাইলে সেভ করা
        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(updated_m3u)

        print(f"✅ playlist_x.m3u generated successfully at {bd_time}")

    except Exception as e:
        print(f"❌ Error fetching playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
