import urllib.request
import re

# সোর্স লিস্ট
SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/bd.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/in.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/categories/sports.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/categories/movies.m3u"
]

def get_clean_name(channel_name):
    """চ্যানেলের নাম নরম্যালাইজ করা (যেমন: BTV HD, BTV SD -> btv)"""
    name = channel_name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)  # ব্র্যাকেট তুলে দেওয়া
    name = re.sub(r'\b(hd|sd|fhd|4k|720p|1080p|stream)\b', '', name) # রেজোলিউশন ট্যাগ বাদ
    name = re.sub(r'[^a-z0-9]', '', name) # স্পেস ও সিম্বল মুছে ফেলা
    return name

def get_clean_url(url):
    """লিংক থেকে টোকেন বা প্যারামিটার ট্রিম করা"""
    return url.split('?')[0].rstrip('/').lower()

# ফিল্টারিং ট্র্যাকার
saved_channels = {} # {clean_name: (metadata, stream_url)}
seen_urls = set()

print("Filtering unique channels and links...")

for src in SOURCES:
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
                        
                        # চ্যানেলের নাম বের করা
                        raw_name = metadata.split(',')[-1].strip() if ',' in metadata else ""
                        clean_name = get_clean_name(raw_name)
                        clean_url = get_clean_url(stream_url)
                        
                        # শর্ত: ইউআরএল বা চ্যানেল নাম আগে সেভ না হয়ে থাকলে তবেই যুক্ত হবে
                        if stream_url.startswith("http") and clean_name:
                            if clean_name not in saved_channels and clean_url not in seen_urls:
                                saved_channels[clean_name] = (metadata, stream_url)
                                seen_urls.add(clean_url)
                        i += 1
                i += 1
        print(f"Loaded source: {src}")
    except Exception as e:
        print(f"Error loading {src}: {e}")

# M3U ফাইল প্রস্তুতকরণ
m3u_output = "#EXTM3U\n"
for metadata, stream_url in saved_channels.values():
    m3u_output += f"{metadata}\n{stream_url}\n"

# ফাইল রাইট করা
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_output)

print(f"\nDone! Total Strictly Unique Channels: {len(saved_channels)}")
