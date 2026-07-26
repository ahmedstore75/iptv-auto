import urllib.request

# =========================================================================
# ১. আপনার কাস্টম সোর্স লিস্ট
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

CATEGORY_ORDER = ["Bangla", "Sports", "Hindi", "English", "Movies", "India"]
DEFAULT_LOGO = "https://raw.githubusercontent.com/iptv-org/iptv/master/assets/icons/iptv.png"

def get_clean_url(url):
    """শুধুমাত্র স্ট্রিম URL ট্রিম করা"""
    return url.strip().split('?')[0].rstrip('/').lower()

all_channels = []
seen_m3u8_urls = set()  # শুধুমাত্র .m3u8 স্ট্রিম লিংক মেমোরিতে ট্র্যাক রাখার জন্য

print("Processing sources... Ensuring 1 unique .m3u8 link max 1 time.")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for source in MY_CUSTOM_SOURCES:
    category_name = source["category"]
    src_url = source["url"]
    try:
        req = urllib.request.Request(src_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
            lines = content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    metadata = line
                    if i + 1 < len(lines):
                        stream_url = lines[i + 1].strip()
                        clean_url = get_clean_url(stream_url)
                        
                        # ১. লিঙ্কটি অবশ্যই http/https হতে হবে এবং .m3u8 থাকতে হবে
                        if stream_url.startswith("http") and ".m3u8" in clean_url:
                            
                            # ২. .m3u8 স্ট্রিম লিঙ্কটি আগে এসেছে কি না তা ফিল্টার করা
                            if clean_url not in seen_m3u8_urls:
                                seen_m3u8_urls.add(clean_url)  # ইউনিক .m3u8 সেভ করে রাখা হলো
                                
                                # ক্যাটাগরি ফিক্স
                                if 'group-title="' not in metadata or 'group-title=""' in metadata:
                                    metadata = metadata.replace('#EXTINF:-1', f'#EXTINF:-1 group-title="{category_name}"')
                                
                                # লোগো সংক্রান্ত কাজ (অরিজিনাল লোগো লিঙ্ক যেমন ছিল তেমনি থাকবে)
                                if 'tvg-logo=""' in metadata:
                                    metadata = metadata.replace('tvg-logo=""', f'tvg-logo="{DEFAULT_LOGO}"')
                                elif 'tvg-logo="' not in metadata:
                                    metadata = metadata.replace('#EXTINF:-1', f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}"')
                                
                                all_channels.append((category_name, metadata, stream_url))
                        i += 1
                i += 1
    except Exception as e:
        print(f"Error reading source ({src_url}): {e}")

# নির্ধারিত ক্যাটাগরি অর্ডারে সাজানো
def sort_key(item):
    category = item[0]
    return CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)

all_channels.sort(key=sort_key)

# M3U ফাইলে সেভ করা
m3u_output = "#EXTM3U\n"
for category, metadata, stream_url in all_channels:
    m3u_output += f"{metadata}\n{stream_url}\n"

with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_output)

print(f"Done! Created playlist.m3u with {len(all_channels)} unique .m3u8 streams.")
