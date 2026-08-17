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

# Country Patterns
BD_PATTERN = re.compile(r'(?i)\b(BD|BANGLADESH|BANGLA)\b')
IN_PATTERN = re.compile(r'(?i)\b(IN|INDIA|INDIAN)\b')
PK_PATTERN = re.compile(r'(?i)\b(PK|PAK|PAKISTAN|PAKISTANI)\b')

# 🚫 STRICT ADULT / 18+ EXCLUSION PATTERN (১৮+ ও এডাল্ট কন্টেন্ট ব্লক)
ADULT_EXCLUDE_PATTERN = re.compile(
    r'(?i)(\b18\+|\bADULT\b|\bXXX\b|\bPORN\b|\bEROTIC\b|\bEXPLICIT\b|\bSEX\b|\bNUDE\b|\bNIGHT\b|\bPLAYBOY\b|\bBRAZZERS\b|\bDESI\s*HOT\b)'
)

# 🚫 STRICT VOD / MOVIE / YEAR-BASED EXCLUSION PATTERN (সাল যুক্ত মুভি লিস্ট ও ভিওডি ব্লক)
VOD_EXCLUDE_PATTERN = re.compile(
    r'(?i)(MOVIE|MOVIES|CINEMA|FILM|FILMS|FLIX|HBO|GOLD|MAX|CINE|CINEPLEX|TALKIES|ACTION|HOLLYWOOD|BOLLYWOOD|TOLLYWOOD|DHALLYWOOD|SERIES|SEASON|EPISODE|VOD|DUBBED|DUAL\s*AUDIO|WEB-DL|HDRIP|BLURAY|\b202[0-9]\b|\b201[0-9]\b)'
)

# 📺 POPULAR LIVE TV NETWORKS (শুধুমাত্র মূল লাইভ টিভি চ্যানেল)
POPULAR_LIVE_NETWORKS = re.compile(
    r'(?i)(STAR\s*PLUS|STAR\s*JALSHA|ZEE\s*TV|ZEE\s*BANGLA|SONY\s*SAB|SONY\s*ENTERTAINMENT|COLORS\s*TV|COLORS\s*BANGLA|SUN\s*TV|ARY\s*DIGITAL|GEO\s*TV|HUM\s*TV|PTV\s*HOME|EXPRESS|DUNYA|SAMAA|NEWS|SOMOY|JAMUNA|INDEPENDENT|ATN|NTV|RTV|CHANNEL\s*I|DEEPTO|MUSIC|GANA|SONG|DRAMA)'
)

# ⚽ SPORTS PATTERN
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

def normalize_channel_name(extinf_line):
    """
    চ্যানেলের নাম থেকে HD, SD, FHD, 4K, BD, IN ইত্যাদি বাদ দিয়ে ইউনিক নাম বের করা।
    """
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
    duplicate_count = 0
    movie_vod_blocked = 0
    adult_blocked = 0
    
    current_extinf = ""
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif not line_str.startswith("#") and current_extinf:
            
            # ১. ১৮+ / এডাল্ট কন্টেন্ট থাকলে সাথে সাথে ব্লক
            if ADULT_EXCLUDE_PATTERN.search(current_extinf) or ADULT_EXCLUDE_PATTERN.search(line_str):
                adult_blocked += 1
                current_extinf = ""
                continue

            # ২. মুভি, সাল যুক্ত ক্যাটাগরি (২০২৫, ২০২৬ ইত্যাদি) বা ভিওডি ব্লক
            is_vod_url = "/movie/" in line_str or "/series/" in line_str or line_str.endswith(('.mp4', '.mkv', '.avi'))
            is_movie_or_year_group = bool(VOD_EXCLUDE_PATTERN.search(current_extinf))
            
            if is_vod_url or is_movie_or_year_group:
                movie_vod_blocked += 1
                current_extinf = ""
                continue

            # ৩. ডুপ্লিকেট চ্যানেল বাদ দেওয়া
            channel_key = normalize_channel_name(current_extinf)
            if line_str in seen_urls or (channel_key and channel_key in seen_channel_names):
                duplicate_count += 1
                current_extinf = ""
                continue
                
            is_bd = bool(BD_PATTERN.search(current_extinf))
            is_in = bool(IN_PATTERN.search(current_extinf))
            is_pk = bool(PK_PATTERN.search(current_extinf))
            is_sports = bool(SPORTS_PATTERN.search(current_extinf))
            is_popular = bool(POPULAR_LIVE_NETWORKS.search(current_extinf))
            
            added = False
            
            # 🇧🇩 ১. বাংলাদেশের লাইভ চ্যানেল
            if is_bd:
                bd_lines.extend([current_extinf, line_str])
                added = True
            
            # 🇮🇳 ২. ইন্ডিয়ার জনপ্রিয় লাইভ চ্যানেল ও স্পোর্টস
            elif is_in and (is_popular or is_sports):
                in_lines.extend([current_extinf, line_str])
                added = True
            
            # 🇵🇰 ৩. পাকিস্তানের জনপ্রিয় লাইভ চ্যানেল ও স্পোর্টস
            elif is_pk and (is_popular or is_sports):
                pk_lines.extend([current_extinf, line_str])
                added = True
            
            # ⚽ ৪. অন্যান্য দেশের স্পোর্টস চ্যানেল
            elif is_sports:
                other_sports_lines.extend([current_extinf, line_str])
                added = True
            
            if added:
                seen_urls.add(line_str)
                if channel_key:
                    seen_channel_names.add(channel_key)
                
            current_extinf = ""
            
    total_added = len(seen_urls)
    print(f"📊 Filtering Summary:")
    print(f"   - 🔞 Adult/18+ Blocked: {adult_blocked}")
    print(f"   - 🚫 Movies/VODs/Year-based lists Blocked: {movie_vod_blocked}")
    print(f"   - 🔄 Duplicates Removed: {duplicate_count}")
    print(f"   - ✅ Total Pure Live TV Channels Added: {total_added}")
    print(f"   ----------------------------------")
    print(f"   - 🇧🇩 Live BD Channels: {len(bd_lines)//2}")
    print(f"   - 🇮🇳 Popular IN Live & Sports: {len(in_lines)//2}")
    print(f"   - 🇵🇰 Popular PK Live & Sports: {len(pk_lines)//2}")
    print(f"   - ⚽ Other World Sports: {len(other_sports_lines)//2}")

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
        
        header_comment = f"# 📦 Pure Live TV Playlist (No Adult / No Movies)\n# ⏰ Updated time: {bd_time}\n"
        updated_m3u = updated_m3u.replace("#EXTM3U", f"#EXTM3U\n{header_comment}", 1)

        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(updated_m3u)

        print(f"✅ playlist_x.m3u generated successfully at {bd_time}")

    except Exception as e:
        print(f"❌ Error fetching playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
