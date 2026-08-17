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

# 🇧🇩 ১. বাংলাদেশ জনপ্রিয় স্যাটেলাইট টিভি চ্যানেল
BD_POPULAR = re.compile(
    r'(?i)(BTV|CHANNEL\s*I|NTV|RTV|ATN\s*BANGLA|ATN\s*NEWS|SOMOY|JAMUNA|INDEPENDENT|EKATTOR|DBC\s*NEWS|DEEPTO|GAZI\s*TV|GTV|T\s*SPORTS|MAASRANGA|BANGLAVISION|BOISHAKHI|MY\s*TV|ASIAN\s*TV|MOHONA|CHANNEL\s*24|NEWS24|BIJOY|DESH\s*TV|SA\s*TV|DURANTO|NEXUS)'
)

# 🇮🇳 ২. ইন্ডিয়া জনপ্রিয় স্যাটেলাইট টিভি চ্যানেল
IN_POPULAR = re.compile(
    r'(?i)(STAR\s*PLUS|STAR\s*JALSHA|ZEE\s*TV|ZEE\s*BANGLA|SONY\s*SAB|SET\s*INDIA|SONY\s*ENTERTAINMENT|COLORS\s*TV|COLORS\s*BANGLA|SUN\s*TV|STAR\s*SPORTS|SONY\s*SPORTS|SONY\s*TEN|SPORTS\s*18|AAJ\s*TAK|NDTV|REPUBLIC|ABP\s*ANANDA|ZEE\s*24\s*GHANTA|NEWS18|9XM|MTV)'
)

# 🇵🇰 ৩. পাকিস্তান জনপ্রিয় স্যাটেলাইট টিভি চ্যানেল
PK_POPULAR = re.compile(
    r'(?i)(GEO\s*NEWS|GEO\s*TV|GEO\s*SUPER|ARY\s*DIGITAL|ARY\s*NEWS|HUM\s*TV|PTV\s*HOME|PTV\s*NEWS|PTV\s*SPORTS|TEN\s*SPORTS|SAMAA|EXPRESS\s*NEWS|DUNYA\s*NEWS)'
)

# ⚽ ৪. আন্তর্জাতিক পপুলার স্পোর্টস লাইভ চ্যানেল
WORLD_SPORTS = re.compile(
    r'(?i)(BEIN\s*SPORTS|SKY\s*SPORTS|SUPERSPORT|WILLOW|EUROSPORT|FOX\s*SPORTS|ASTRO\s*SUPERSPORT|DAZN\s*[0-9]|DAZN\s*1|DAZN\s*2|CANAL\+\s*SPORT|TNT\s*SPORTS|ESPN)'
)

# 🚫 STRICT SERIES / EPISODE / VOD FILTER (S01 E01, Season, Episode ফিল্টার করে বাদ দেবে)
EPISODE_VOD_PATTERN = re.compile(
    r'(?i)('
    r'\bs\d{1,2}\s*e\d{1,2}\b|'         # S01 E01, S1 E1
    r'\bs\d{1,2}e\d{1,2}\b|'           # S01E01
    r'\bs\d{2}\b|\be\d{2}\b|'            # S01, E01
    r'\bep\d+\b|\bepisode\b|\bseason\b|' # EP01, Episode, Season
    r'(\(\d{4}\))|'                    # (1997), (2024) ইত্যাদি সাল ব্র্যাকেটে
    r'MOVIE|MOVIES|CINEMA|FILM|FLIX|HBO|GOLD|MAX|CINE|CINEPLEX|TALKIES|ACTION|XXX|18\+|ADULT|PORN|TEST|MIX|WEB-SERIES'
    r')'
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

def normalize_channel_name(extinf_line):
    if ',' in extinf_line:
        name = extinf_line.split(',')[-1]
    else:
        name = extinf_line
    name = name.lower()
    name = re.sub(r'(?i)\b(bd|in|pk|hd|fhd|sd|4k|hevc|1080p|720p|50fps|raw|vip|backup|server\d*)\b', '', name)
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def filter_requested_channels(content):
    lines = content.splitlines()
    
    bd_lines = []
    in_lines = []
    pk_lines = []
    other_sports_lines = []
    
    seen_urls = set()
    seen_channel_names = set()
    
    current_extinf = ""
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif not line_str.startswith("#") and current_extinf:
            
            # ১. লিঙ্কটি যদি সিরিজ (/series/) বা মুভির (/movie/) ভিডিও লিঙ্ক হয়
            if "/series/" in line_str or "/movie/" in line_str or line_str.endswith(('.mp4', '.mkv', '.avi')):
                current_extinf = ""
                continue

            # ২. নামের মধ্যে S01, E01, Season, Episode, বা সাল থাকলে ব্লক
            if EPISODE_VOD_PATTERN.search(current_extinf) or EPISODE_VOD_PATTERN.search(line_str):
                current_extinf = ""
                continue

            # ৩. ডুপ্লিকেট চ্যানেল বাদ দেওয়া
            channel_key = normalize_channel_name(current_extinf)
            if line_str in seen_urls or (channel_key and channel_key in seen_channel_names):
                current_extinf = ""
                continue
                
            # ৪. শুধুমাত্র আসল লাইভ স্যাটেলাইট টিভি চ্যানেল ম্যাচিং
            is_bd = bool(BD_POPULAR.search(current_extinf))
            is_in = bool(IN_POPULAR.search(current_extinf))
            is_pk = bool(PK_POPULAR.search(current_extinf))
            is_sports = bool(WORLD_SPORTS.search(current_extinf))
            
            added = False
            
            if is_bd:
                bd_lines.extend([current_extinf, line_str])
                added = True
            elif is_in:
                in_lines.extend([current_extinf, line_str])
                added = True
            elif is_pk:
                pk_lines.extend([current_extinf, line_str])
                added = True
            elif is_sports:
                other_sports_lines.extend([current_extinf, line_str])
                added = True
            
            if added:
                seen_urls.add(line_str)
                if channel_key:
                    seen_channel_names.add(channel_key)
                
            current_extinf = ""
            
    total_added = len(seen_urls)
    print(f"📊 Filtering Summary (Pure Live TV Only):")
    print(f"   - ✅ Total Live Channels Added: {total_added}")
    print(f"   - 🇧🇩 Live BD Satellite Channels: {len(bd_lines)//2}")
    print(f"   - 🇮🇳 Live IN Satellite Channels: {len(in_lines)//2}")
    print(f"   - 🇵🇰 Live PK Satellite Channels: {len(pk_lines)//2}")
    print(f"   - ⚽ World Sports Live Channels: {len(other_sports_lines)//2}")

    filtered_lines = ["#EXTM3U"] + bd_lines + in_lines + pk_lines + other_sports_lines
    return "\n".join(filtered_lines)

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)
        filtered_content = filter_requested_channels(content)

        # স্ট্রিম লিঙ্ক রূপান্তর
        stream_pattern = re.compile(
            rf"{re.escape(BASE_URL)}/(?:live/)?{re.escape(USERNAME)}/{re.escape(PASSWORD)}/([0-9a-zA-Z_-]+)(\.m3u8|\.ts)?"
        )
        
        def replace_url(match):
            stream_id = match.group(1)
            return f"{WORKER_DOMAIN}/{stream_id}/index.m3u8"

        updated_m3u = stream_pattern.sub(replace_url, filtered_content)

        # লোগো লিঙ্ক রূপান্তর
        logo_pattern = re.compile(rf'tvg-logo="{re.escape(BASE_URL)}([^"]+)"')
        updated_m3u = logo_pattern.sub(rf'tvg-logo="{WORKER_DOMAIN}\1"', updated_m3u)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        header_comment = f"# 📦 Pure Live Satellite TV Playlist (No Series / No Episodes)\n# ⏰ Updated time: {bd_time}\n"
        updated_m3u = updated_m3u.replace("#EXTM3U", f"#EXTM3U\n{header_comment}", 1)

        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(updated_m3u)

        print(f"✅ playlist_x.m3u generated successfully at {bd_time}")

    except Exception as e:
        print(f"❌ Error fetching playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
