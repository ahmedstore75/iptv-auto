import re
import json
import urllib.request
import time
from datetime import datetime, timezone, timedelta

# --- CONFIG ---
M3U_SOURCE_URL = "https://iptv-123.fit/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_playlist_content(url, retries=3, delay=5, timeout=60):
    for attempt in range(1, retries + 1):
        try:
            print(f"🔄 Attempt {attempt}/{retries}: Downloading playlist from URL...")
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

def parse_m3u_to_json(content):
    lines = content.splitlines()
    channels = []
    
    current_extinf = ""
    current_kodiprops = {}
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
            current_kodiprops = {} # নতুন চ্যানেলের জন্য রিসেট করা
        elif line_str.startswith("#KODIPROP"):
            # KODIPROP তথ্য পার্স করা
            parts = line_str.replace("#KODIPROP:", "").strip().split("=", 1)
            if len(parts) == 2:
                current_kodiprops[parts[0].strip()] = parts[1].strip()
        elif not line_str.startswith("#") and current_extinf:
            # এটি স্ট্রিম লিংক
            stream_url = line_str
            
            tvg_id = ""
            tvg_logo = ""
            group_title = ""
            name = ""
            
            # tvg-id এক্সট্রাক্ট করা
            id_match = re.search(r'tvg-id="([^"]*)"', current_extinf)
            if id_match:
                tvg_id = id_match.group(1)
                
            # tvg-logo এক্সট্রাক্ট করা
            logo_match = re.search(r'tvg-logo="([^"]*)"', current_extinf)
            if logo_match:
                tvg_logo = logo_match.group(1)
                
            # group-title এক্সট্রাক্ট করা
            group_match = re.search(r'group-title="([^"]*)"', current_extinf)
            if group_match:
                group_title = group_match.group(1)
                
            # চ্যানেলের নাম পরিষ্কার করা (ঘড়ি বা কমা মুছে ফেলা)
            if ',' in current_extinf:
                name_part = current_extinf.split(',', 1)[1].strip()
                name = re.sub(r'^[⏱️·,\s]+', '', name_part)
            
            channel_data = {
                "tvg_id": tvg_id,
                "tvg_logo": tvg_logo,
                "group_title": group_title,
                "name": name,
                "kodiprop": current_kodiprops,
                "url": stream_url
            }
            
            channels.append(channel_data)
            current_extinf = ""
            current_kodiprops = {}
            
    return channels

def fetch_and_generate_json():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)
        channels = parse_m3u_to_json(content)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        output_data = {
            "updated_time": bd_time,
            "total_channels": len(channels),
            "channels": channels
        }

        # জেসন ফাইলটি playlist_x.json নামে সেভ করা হচ্ছে
        with open("playlist_x.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"✅ playlist_x.json generated successfully at {bd_time} (Total Channels: {len(channels)})")

    except Exception as e:
        print(f"❌ Error generating JSON playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate_json()
