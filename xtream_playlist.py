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
PK_PATTERN = re.compile(r'(?i)\b(PK|PAK|PAKISTAN|PAKISTANI)\b')

# ইন্ডিয়া ও পাকিস্তানের জনপ্রিয় নেটওয়ার্ক/ক্যাটাগরি
POPULAR_NETWORKS = re.compile(
    r'(?i)(STAR|ZEE|SONY|COLORS|SUN|SAB|COLOURS|ARY|GEO|HUM|PTV|EXPRESS|DUNYA|SAMAA|NEWS|MOVIE|MOVIES|CINEMA|FILM|MUSIC|GANA|SONG|DRAMA)'
)

# সকল স্পোর্টস চ্যানেল
SPORTS_PATTERN = re.compile(
    r'(?i)(SPORT|SPORTS|CRICKET|FOOTBALL|SOCCER|T20|IPL|BEIN|ESPN|SUPERSPORT|WILLOW|TEN\s*SPORTS|STAR\s*SPORTS|SONY\s*SPORTS|SKY\s*SPORTS|FOX\s*SPORTS|CANAL\+\s*SPORT|ASTRO|EUROSPORT|DAZN|WWE|RACING|GOLF|TENNIS|PTV\s*SPORTS|GEO\s*SUPER)'
)

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
    
    bd_lines = []
    in_lines = []
    pk_lines = []
    other_sports_lines = []
    
    # ডুপ্লিকেট চ্যানেল আটকানোর জন্য Set
    seen_urls = set()
    duplicate_count = 0
    
    current_extinf = ""
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif not line_str.startswith("#") and current_extinf:
            # ডুপ্লিকেট ইউআরএল ফিল্টারিং
            if line_str in seen_urls:
                duplicate_count += 1
                current_extinf = ""
                continue
                
            is_vod = "/movie/" in line_str or "/series/" in line_str
            
            if not is_vod:
                is_bd = bool(BD_PATTERN.search(current_extinf))
                is_in = bool(IN_PATTERN.search(current_extinf))
                is_pk = bool(PK_PATTERN.search(current_extinf))
                is_sports = bool(SPORTS_PATTERN.search(current_extinf))
                is_popular = bool(POPULAR_NETWORKS.search(current_extinf))
                
                added = False
                # ১. বাংলাদেশের সকল চ্যানেল
                if is_bd:
                    bd_lines.extend([current_extinf, line_str])
                    added = True
                
                # ২. ইন্ডিয়ার জনপ্রিয় চ্যানেল এবং স্পোর্টস
                elif is_in and (is_popular or is_sports):
                    in_lines.extend([current_extinf, line_str])
                    added = True
                
                # ৩. পাকিস্তানের জনপ্রিয় চ্যানেল এবং স্পোর্টস
                elif is_pk and (is_popular or is_sports):
                    pk_lines.extend([current_extinf, line_str])
                    added = True
                
                # ৪. অন্যান্য দেশের স্পোর্টস চ্যানেল
                elif is_sports:
                    other_sports_lines.extend([current_extinf, line_str])
                    added = True
                
                if added:
                    seen_urls.add(line_str)
                
            current_extinf = ""
            
    total_added = len(seen_urls)
    print(f"📊 Total {total_added} unique channels filtered (Removed {duplicate_count} duplicates).")
    print(f"   - 🇧🇩 All BD Channels: {len(bd_lines)//2}")
    print(f"   - 🇮🇳 Popular IN Channels & Sports: {len(in_lines)//2}")
    print(f"   - 🇵🇰 Popular PK Channels & Sports: {len(pk_lines)//2}")
    print(f"   - ⚽ Other World Sports: {len(other_sports_lines)//2}")

    filtered_lines = ["#EXTM3U"] + bd_lines + in_lines + pk_lines + other_sports_lines
    return "\n".join(filtered_lines)

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)

        # ১. ফিল্টারিং, সাজানো ও ডুপ্লিকেট দূর করা
        filtered_content = filter_requested_channels(content)

        # ২. স্ট্রিম লিঙ্ক রূপান্তর: WORKER_DOMAIN/stream_id/index.m3u8
        stream_pattern = re.compile(
            rf"{re.escape(BASE_URL)}/(?:live/)?{re.escape(USERNAME)}/{re.escape(PASSWORD)}/([0-9a-zA-Z_-]+)(\.m3u8|\.ts)?"
        )
        
        def replace_url(match):
            stream_id = match.group(1)
            return f"{WORKER_DOMAIN}/{stream_id}/index.m3u8"

        updated_m3u = stream_pattern.sub(replace_url, filtered_content)

        # ৩. লোগো লিঙ্ক রূপান্তর
        logo_pattern = re.compile(rf'tvg-logo="{re.escape(BASE_URL)}([^"]+)"')
        updated_m3u = logo_pattern.sub(rf'tvg-logo="{WORKER_DOMAIN}\1"', updated_m3u)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        header_comment = f"# 📦 Custom Playlist (De-duplicated & Sorted)\n# ⏰ Updated time: {bd_time}\n"
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
