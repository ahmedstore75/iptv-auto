import re
import urllib.request
import time
from datetime import datetime, timezone, timedelta

# --- CONFIG ---
BASE_URL = "http://filex.me:8080"
USERNAME = "3114654477"
PASSWORD = "5787654467"

M3U_SOURCE_URL = f"{BASE_URL}/get.php?username={USERNAME}&password={PASSWORD}&type=m3u_plus&output=m3u8"
WORKER_DOMAIN = "https://saiptvlive.ahmed-bd-org.workers.dev"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ফিল্টারিং প্যাটার্ন
BD_PATTERN = re.compile(r'(?i)\b(BD|BANGLADESH|BANGLA)\b')
IN_PATTERN = re.compile(r'(?i)\b(IN|INDIA|INDIAN)\b')
IN_GENRE_PATTERN = re.compile(r'(?i)(MOVIE|MOVIES|CINEMA|FILM|MUSIC|GANA|SONG|SPORT|SPORTS|CRICKET|FOOTBALL)')
PK_PATTERN = re.compile(r'(?i)\b(PK|PAKISTAN|PAK)\b')
SPORTS_PATTERN = re.compile(r'(?i)(SPORT|SPORTS|CRICKET|FOOTBALL|SOCCER|T20|IPL|BEIN|ESPN|SUPERSPORT|WILLOW|TEN\s*SPORTS|STAR\s*SPORTS|SONY\s*SPORTS|SKY\s*SPORTS|FOX\s*SPORTS|CANAL\+\s*SPORT|ASTRO|EUROSPORT|DAZN|WWE|RACING|GOLF|TENNIS)')

def fetch_playlist_content(url, retries=3, delay=5, timeout=60):
    for attempt in range(1, retries + 1):
        try:
            print(f"🔄 Attempt {attempt}/{retries}: Downloading playlist...")
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                raise e

def filter_and_sort_channels(content):
    lines = content.splitlines()
    
    # দেশভিত্তিক আলাদা ক্যাটাগরি বাকেট
    bd_channels = []
    in_channels = []
    pk_channels = []
    other_sports_channels = []
    
    current_extinf = ""
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif not line_str.startswith("#") and current_extinf:
            is_vod = "/movie/" in line_str or "/series/" in line_str
            
            if not is_vod:
                is_sports = bool(SPORTS_PATTERN.search(current_extinf))
                
                # ১. বাংলাদেশ
                if BD_PATTERN.search(current_extinf):
                    bd_channels.append((current_extinf, line_str))
                # ২. ইন্ডিয়া (মুভি, মিউজিক, স্পোর্টস)
                elif IN_PATTERN.search(current_extinf) and IN_GENRE_PATTERN.search(current_extinf):
                    in_channels.append((current_extinf, line_str))
                # ৩. পাকিস্তান (স্পোর্টস)
                elif PK_PATTERN.search(current_extinf) and is_sports:
                    pk_channels.append((current_extinf, line_str))
                # ৪. অন্যান্য দেশের স্পোর্টস (USA, NZ, AU, World Sports)
                elif is_sports:
                    other_sports_channels.append((current_extinf, line_str))
                    
            current_extinf = ""

    # ক্রমানুসারে একত্রিত করা: BD -> IN -> PK -> Other Sports
    sorted_channels = bd_channels + in_channels + pk_channels + other_sports_channels
    
    filtered_lines = ["#EXTM3U"]
    for extinf, stream_url in sorted_channels:
        filtered_lines.append(extinf)
        filtered_lines.append(stream_url)
        
    print(f"📊 Ordered Total: BD ({len(bd_channels)}), IN ({len(in_channels)}), PK ({len(pk_channels)}), Other Sports ({len(other_sports_channels)})")
    return "\n".join(filtered_lines)

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL)
        sorted_content = filter_and_sort_channels(content)

        # Worker URL রিformatting (/token/index.m3u8)
        pattern = re.compile(rf"{re.escape(BASE_URL)}/([^\s\n\r]+)")
        
        def replace_url(match):
            stream_path = match.group(1).rstrip('/')
            clean_path = re.sub(r'(\.m3u8|\.ts)$', '', stream_path)
            return f"{WORKER_DOMAIN}/{clean_path}/index.m3u8"

        updated_m3u = pattern.sub(replace_url, sorted_content)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        header_comment = f"# 📦 Playlist X (Sorted: BD > IN > PK > Sports)\n# ⏰ Updated: {bd_time}\n"
        updated_m3u = updated_m3u.replace("#EXTM3U", f"#EXTM3U\n{header_comment}", 1)

        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(updated_m3u)

        print(f"✅ playlist_x.m3u updated with strict sequence at {bd_time}")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
