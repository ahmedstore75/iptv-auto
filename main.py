import urllib.request
import re

# =========================================================================
# আপনার পছন্দমতো কাস্টম M3U বা সোর্স লিংকগুলো নিচে দিন
# =========================================================================
MY_CUSTOM_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/bd.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/in.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/categories/sports.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/categories/movies.m3u",
    
    # আপনার অন্য কোনো M3U লিংক থাকলে নিচে যোগ করুন:
    # "https://example.com/my_custom_source.m3u",
]

DEFAULT_LOGO = "https://raw.githubusercontent.com/iptv-org/iptv/master/assets/icons/iptv.png"

def is_stream_working(url):
    """লিংক সত্যিই চালু আছে কিনা নিশ্চিত করা (Real-time Test)"""
    try:
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status in [200, 206, 301, 302]
    except Exception:
        return False

def get_clean_name(channel_name):
    """চ্যানেলের নাম নরম্যালাইজ করা যেন ডুপ্লিকেট সহজে ধরা পড়ে"""
    name = channel_name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = re.sub(r'\b(hd|sd|fhd|4k|720p|1080p|stream|live)\b', '', name)
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def get_clean_url(url):
    """ইউআরএল থেকে ডাইনামিক টোকেন/প্যারামিটার ফেলে দিয়ে বেসিক লিংক বের করা"""
    return url.split('?')[0].rstrip('/').lower()

# ১. ইউনিক চ্যানেল এবং লিংক ট্র্যাক করার জন্য
saved_channels = {}  # {clean_channel_name: (metadata, stream_url)}
seen_clean_urls = set()  # ডুপ্লিকেট লিংক ট্র্যাকিং

print("Filtering and testing streams... (Strictly 1 Channel = 1 Working Link)\n")

for src in MY_CUSTOM_SOURCES:
    try:
        req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
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
                        
                        # কন্ডিশন ১: চ্যানেলের নাম এবং স্ট্রিম লিংক যেন বৈধ হয়
                        if stream_url.startswith("http") and clean_name:
                            # কন্ডিশন ২: এই চ্যানেলটি বা এই লিংকটি আগে থেকেই আমাদের লিস্টে যুক্ত আছে কিনা
                            if clean_name not in saved_channels and clean_url not in seen_clean_urls:
                                
                                # লোগো ফিল্টারিং
                                if 'tvg-logo="' not in metadata or 'tvg-logo=""' in metadata:
                                    metadata = metadata.replace('#EXTINF:-1', f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}"')

                                print(f"Testing: {raw_name} ...", end=" ")
                                
                                # কন্ডিশন ৩: লিংকটি বর্তমানে ওয়ার্কিং কিনা
                                if is_stream_working(stream_url):
                                    saved_channels[clean_name] = (metadata, stream_url)
                                    seen_clean_urls.add(clean_url)
                                    print("[ADDED - WORKING]")
                                else:
                                    print("[SKIPPED - DEAD]")
                        i += 1
                i += 1
    except Exception as e:
        print(f"Failed to fetch source ({src}): {e}")

# M3U প্লেলিস্ট জেনারেট করা
m3u_output = "#EXTM3U\n"
for metadata, stream_url in saved_channels.values():
    m3u_output += f"{metadata}\n{stream_url}\n"

with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_output)

print(f"\nSuccess! Saved exactly {len(saved_channels)} unique channels with 100% active links.")
