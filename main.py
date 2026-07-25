import urllib.request
import re
from concurrent.futures import ThreadPoolExecutor

# =========================================================================
# ১. আপনার কাস্টম সোর্স লিস্ট (সঠিক লিঙ্ক ও সিকোয়েন্স সহ)
# =========================================================================
MY_CUSTOM_SOURCES = [
    # ১. বাংলাদেশ ও ইন্ডিয়ান বাংলা
    {"category": "Bangla", "url": "https://raw.githubusercontent.com/ahmedstore75/Iptvbdlive/refs/heads/main/mixiptvchannel.m3u"},
    {"category": "Bangla", "url": "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/Combined_Live_TV.m3u"},
    
    # ২. স্পোর্টস চ্যানেল
    {"category": "Sports", "url": "https://raw.githubusercontent.com/IPTVFlixBD/OopsTv/refs/heads/main/all-sports.m3u"},
    
    # ৩. হিন্দি চ্যানেল
    {"category": "Hindi", "url": "https://raw.githubusercontent.com/abusaeeidx/Mrgify-BDIX-IPTV/main/playlist.m3u"},
    
    # ৪. ইংলিশ চ্যানেল
    {"category": "English", "url": "https://raw.githubusercontent.com/abusaeeidx/IPTV-Scraper-Zilla/refs/heads/main/LGTV-Schedule.m3u"},
    
    # ৫. অন্যান্য মুভি ও ভারত
    {"category": "Movies", "url": "https://raw.githubusercontent.com/sanjoykb/-KB-TV-Playlist/refs/heads/main/Github%20Auto%20Update%20Channel.m3u"},
    {"category": "India", "url": "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/SM%20All%20TV.m3u"},
]

# ক্যাটাগরি অনুযায়ী সাজানোর অগ্রাধিকার
CATEGORY_ORDER = ["Bangla", "Sports", "Hindi", "English", "Movies", "India"]
DEFAULT_LOGO = "https://raw.githubusercontent.com/iptv-org/iptv/master/assets/icons/iptv.png"

def is_stream_working(item):
    """কাস্টম ও BDIX লিংকের জন্য ২.৫ সেকেন্ড টাইমআউট সহ সমান্তরাল চেকিং"""
    category, clean_name, metadata, stream_url, raw_name = item
    try:
        req = urllib.request.Request(
            stream_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=2.5) as response:
            if response.status in [200, 206, 301, 302]:
                print(f"[WORKING] ({category}) -> {raw_name}")
                return item
    except Exception:
        pass
    return None

def get_clean_name(channel_name):
    name = channel_name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'\b(hd|sd|fhd|4k|720p|1080p|stream|live)\b', '', name)
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def get_clean_url(url):
    return url.split('?')[0].rstrip('/').lower()

raw_candidates = []
seen_names = set()
seen_urls = set()

print("Parsing custom sources...")

for source in MY_CUSTOM_SOURCES:
    category_name = source["category"]
    src_url = source["url"]
    try:
        req = urllib.request.Request(src_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
            lines = content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    metadata = line
                    if i + 1 < len(lines):
                        stream_url = lines[i + 1].strip()
                        
                        raw_name = metadata.split(',')[-1].strip() if ',' in metadata else ""
                        clean_name = get_clean_name(raw_name)
                        clean_url = get_clean_url(stream_url)
                        
                        if stream_url.startswith("http") and clean_name:
                            # ডুপ্লিকেট ফিল্টারিং (১ চ্যানেল = ১টি লিংক)
                            if clean_name not in seen_names and clean_url not in seen_urls:
                                seen_names.add(clean_name)
                                seen_urls.add(clean_url)
                                
                                # গ্রুপ টাইটেল যোগ
                                if 'group-title="' not in metadata or 'group-title=""' in metadata:
                                    metadata = metadata.replace('#EXTINF:-1', f'#EXTINF:-1 group-title="{category_name}"')
                                
                                # লোগো ফিক্স
                                if 'tvg-logo=""' in metadata:
                                    metadata = metadata.replace('tvg-logo=""', f'tvg-logo="{DEFAULT_LOGO}"')
                                elif 'tvg-logo="' not in metadata:
                                    metadata = metadata.replace('#EXTINF:-1', f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}"')
                                
                                raw_candidates.append((category_name, clean_name, metadata, stream_url, raw_name))
                        i += 1
                i += 1
    except Exception as e:
        print(f"Error reading ({src_url}): {e}")

print(f"\nTesting {len(raw_candidates)} channels...")

working_channels = []

# Multithreading দিয়ে স্পিড চেক
with ThreadPoolExecutor(max_workers=12) as executor:
    results = executor.map(is_stream_working, raw_candidates)
    for res in results:
        if res:
            working_channels.append(res)

# নির্দিষ্ট ক্যাটাগরি অনুযায়ী সাজানো
def sort_key(item):
    category = item[0]
    return CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)

working_channels.sort(key=sort_key)

# M3U আউটপুট রাইট
m3u_output = "#EXTM3U\n"
for category, clean_name, metadata, stream_url, raw_name in working_channels:
    m3u_output += f"{metadata}\n{stream_url}\n"

with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_output)

print(f"\nDone! Playlist created with {len(working_channels)} active channels.")
