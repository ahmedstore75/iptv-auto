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

# 📌 চ্যানেল প্যাটার্ন ও নির্দিষ্ট গ্রুপ টাইটেল
BANGLA_NEWS_PAT = re.compile(r'(?i)(SOMOY|JAMUNA|INDEPENDENT|EKATTOR|DBC\s*NEWS|CHANNEL\s*24|NEWS24|ATN\s*NEWS)')
BANGLA_KIDS_PAT = re.compile(r'(?i)(DURANTO)')
BANGLA_ENT_PAT = re.compile(r'(?i)(BTV|CHANNEL\s*I|NTV|RTV|ATN\s*BANGLA|DEEPTO|GAZI\s*TV|GTV|MAASRANGA|BANGLAVISION|BOISHAKHI|MY\s*TV|ASIAN\s*TV|MOHONA|BIJOY|DESH\s*TV|SA\s*TV|NEXUS|\bBD\b|\bBANGLA\b|\bBANGLADESH\b)')
INDIAN_BANGLA_PAT = re.compile(r'(?i)(STAR\s*JALSHA|ZEE\s*BANGLA|COLORS\s*BANGLA|ABP\s*ANANDA|ZEE\s*24\s*GHANTA)')

SPORTS_PAT = re.compile(r'(?i)(T\s*SPORTS|SPORT|SPORTS|CRICKET|FOOTBALL|SOCCER|T20|IPL|BEIN|ESPN|SUPERSPORT|WILLOW|TEN\s*SPORTS|STAR\s*SPORTS|SONY\s*SPORTS|SONY\s*TEN|SPORTS\s*18|SKY\s*SPORTS|FOX\s*SPORTS|CANAL\+\s*SPORT|ASTRO|EUROSPORT|DAZN|WWE|PTV\s*SPORTS|GEO\s*SUPER)')

# 🎬 পপুলার ইন্ডিয়ান মুভি চ্যানেল ফিল্টার
INDIAN_MOVIES_PAT = re.compile(r'(?i)(ZEE\s*CINEMA|SONY\s*MAX\s*2|SONY\s*MAX|STAR\s*GOLD\s*2|STAR\s*GOLD\s*SELECT|STAR\s*GOLD|GOLDMINES|COLORS\s*CINEPLEX|ZEE\s*ANMOL\s*CINEMA|ZEE\s*ACTION|SONY\s*WAH|STAR\s*UTSAV\s*MOVIES)')

# 🎵 ইন্ডিয়ান পপুলার মিউজিক চ্যানেল ফিল্টার
INDIAN_MUSIC_PAT = re.compile(r'(?i)(9XM|9X\s*JALWA|9XJALWA|B4U\s*MUSIC|B4U|MASTIII|ZOOM|SONY\s*MIX|MTV\s*BEATS|MTV|MH1|MUSIC\s*INDIA)')

INDIAN_HINDI_PAT = re.compile(r'(?i)(STAR\s*PLUS|ZEE\s*TV|SONY\s*SAB|SET\s*INDIA|SONY\s*ENTERTAINMENT|COLORS\s*TV|SUN\s*TV|AAJ\s*TAK|NDTV|REPUBLIC|NEWS18)')
PAKISTANI_PAT = re.compile(r'(?i)(GEO\s*NEWS|GEO\s*TV|ARY\s*DIGITAL|ARY\s*NEWS|HUM\s*TV|PTV\s*HOME|PTV\s*NEWS|SAMAA|EXPRESS\s*NEWS|DUNYA\s*NEWS)')

# 🚫 VOD / EPISODE / SINGLE MOVIE FILE FILTER (চ্যানেলের নাম ব্লক করবে না)
EPISODE_VOD_PATTERN = re.compile(
    r'(?i)('
    r'\bs\d{1,2}\s*e\d{1,2}\b|'         # S01 E01, S1 E1
    r'\bs\d{1,2}e\d{1,2}\b|'           # S01E01
    r'\bs\d{2}\b|\be\d{2}\b|'            # S01, E01
    r'\bep\d+\b|\bepisode\b|\bseason\b|' # EP01, Episode, Season
    r'(\(\d{4}\))|'                    # (1997), (2024) ইত্যাদি সাল
    r'XXX|18\+|ADULT|PORN|TEST|MIX|WEB-SERIES|WEB\s*SERIES'
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

def set_group_title(extinf_line, group_name):
    if 'group-title="' in extinf_line:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group_name}"', extinf_line)
    else:
        if ',' in extinf_line:
            header, channel_name = extinf_line.split(',', 1)
            return f'{header} group-title="{group_name}",{channel_name}'
        return f'{extinf_line} group-title="{group_name}"'

def filter_requested_channels(content):
    lines = content.splitlines()
    
    groups = {
        "BANGLA NEWS": [],
        "BANGLA ENTERTAINMENT": [],
        "BANGLA KIDS": [],
        "INDIAN BANGLA": [],
        "SPORTS LIVE": [],
        "INDIAN MOVIES": [],
        "INDIAN MUSIC": [],
        "INDIAN HINDI": [],
        "PAKISTANI TV": []
    }
    
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
            
            # ১. ভিওডি/সিরিজ লিংক বাদ
            if "/series/" in line_str or "/movie/" in line_str or line_str.endswith(('.mp4', '.mkv', '.avi')):
                current_extinf = ""
                continue

            # ২. এপিসোড/সাল/১৮+ ফিল্টার
            if EPISODE_VOD_PATTERN.search(current_extinf) or EPISODE_VOD_PATTERN.search(line_str):
                current_extinf = ""
                continue

            # ৩. ডুপ্লিকেট চ্যানেল চেক
            channel_key = normalize_channel_name(current_extinf)
            if line_str in seen_urls or (channel_key and channel_key in seen_channel_names):
                current_extinf = ""
                continue
                
            # ৪. স্বয়ংক্রিয় গ্রুপ ফিল্টারিং
            target_group = None
            
            if BANGLA_NEWS_PAT.search(current_extinf):
                target_group = "BANGLA NEWS"
            elif BANGLA_KIDS_PAT.search(current_extinf):
                target_group = "BANGLA KIDS"
            elif INDIAN_BANGLA_PAT.search(current_extinf):
                target_group = "INDIAN BANGLA"
            elif BANGLA_ENT_PAT.search(current_extinf):
                target_group = "BANGLA ENTERTAINMENT"
            elif SPORTS_PAT.search(current_extinf):
                target_group = "SPORTS LIVE"
            elif INDIAN_MOVIES_PAT.search(current_extinf):
                target_group = "INDIAN MOVIES"
            elif INDIAN_MUSIC_PAT.search(current_extinf):
                target_group = "INDIAN MUSIC"
            elif INDIAN_HINDI_PAT.search(current_extinf):
                target_group = "INDIAN HINDI"
            elif PAKISTANI_PAT.search(current_extinf):
                target_group = "PAKISTANI TV"
                
            if target_group:
                updated_extinf = set_group_title(current_extinf, target_group)
                groups[target_group].extend([updated_extinf, line_str])
                
                seen_urls.add(line_str)
                if channel_key:
                    seen_channel_names.add(channel_key)
                
            current_extinf = ""

    ordered_lines = []
    category_order = [
        "BANGLA NEWS",
        "BANGLA ENTERTAINMENT",
        "BANGLA KIDS",
        "INDIAN BANGLA",
        "SPORTS LIVE",
        "INDIAN MOVIES",
        "INDIAN MUSIC",
        "INDIAN HINDI",
        "PAKISTANI TV"
    ]
    
    total_added = 0
    print("📊 Auto Grouping Summary:")
    for cat in category_order:
        count = len(groups[cat]) // 2
        total_added += count
        print(f"   - 📁 {cat}: {count} channels")
        ordered_lines.extend(groups[cat])

    print(f"✅ Total Saved Live Channels: {total_added}")
    return "\n".join(ordered_lines), total_added

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)
        filtered_content, total_saved = filter_requested_channels(content)

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
        
        # 📌 প্লেলিস্টের উপরে মোট চ্যানেলের কাউন্টিং হেডার
        playlist_header = (
            f"#EXTM3U\n"
            f"# 📊 Total Saved Channels: {total_saved}\n"
            f"# 📦 Auto-Categorized Live Satellite TV Playlist\n"
            f"# ⏰ Updated time: {bd_time}\n"
        )
        
        final_m3u = playlist_header + updated_m3u

        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(final_m3u)

        print(f"✅ playlist_x.m3u generated successfully at {bd_time} (Total Channels: {total_saved})")

    except Exception as e:
        print(f"❌ Error fetching playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
