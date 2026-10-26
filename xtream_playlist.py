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

def clean_extinf_line(extinf_line):
    """
    নামের আগের ঘড়ি (⏱️), ডট (·) বা অতিরিক্ত কমা ও স্পেস মুছে ফেলবে।
    """
    if ',' in extinf_line:
        parts = extinf_line.split(',', 1)
        attributes = parts[0]
        name_part = parts[1].strip()
        cleaned_name = re.sub(r'^[⏱️·,\s]+', '', name_part)
        return f"{attributes},{cleaned_name}"
    return extinf_line

def process_playlist_dual(content):
    lines = content.splitlines()
    m3u_processed_lines = []
    channels_json = []
    
    current_extinf = ""
    current_kodiprops = {}
    total_channels = 0
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
            current_kodiprops = {}
            cleaned_extinf = clean_extinf_line(line_str)
            m3u_processed_lines.append(cleaned_extinf)
        elif line_str.startswith("#KODIPROP"):
            m3u_processed_lines.append(line_str)
            parts = line_str.replace("#KODIPROP:", "").strip().split("=", 1)
            if len(parts) == 2:
                current_kodiprops[parts[0].strip()] = parts[1].strip()
        elif not line_str.startswith("#") and current_extinf:
            stream_url = line_str
            m3u_processed_lines.append(stream_url)
            total_channels += 1
            
            # JSON-এর জন্য ডাটা পার্স করা
            tvg_id = ""
            tvg_logo = ""
            group_title = ""
            name = ""
            
            id_match = re.search(r'tvg-id="([^"]*)"', current_extinf)
            if id_match:
                tvg_id = id_match.group(1)
                
            logo_match = re.search(r'tvg-logo="([^"]*)"', current_extinf)
            if logo_match:
                tvg_logo = logo_match.group(1)
                
            group_match = re.search(r'group-title="([^"]*)"', current_extinf)
            if group_match:
                group_title = group_match.group(1)
                
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
            channels_json.append(channel_data)
            current_extinf = ""
            current_kodiprops = {}
            
    return m3u_processed_lines, channels_json, total_channels

def fetch_and_generate_files():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)
        m3u_lines, channels_json, total_saved = process_playlist_dual(content)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # ১. M3U ফাইল তৈরি
        playlist_header = (
            f"#EXTM3U\n"
            f"# 📊 Total Channels: {total_saved}\n"
            f"# 📦 Complete Playlist with Original Groups & Cleaned Names\n"
            f"# ⏰ Updated time: {bd_time}\n"
        )
        final_m3u = playlist_header + "\n".join(m3u_lines)

        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(final_m3u)
        print(f"✅ playlist_x.m3u generated successfully! (Total Channels: {total_saved})")

        # ২. JSON ফাইল তৈরি (playlist_x.json)
        output_data = {
            "updated_time": bd_time,
            "total_channels": total_saved,
            "channels": channels_json
        }

        with open("playlist_x.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"✅ playlist_x.json generated successfully!")

    except Exception as e:
        print(f"❌ Error generating playlists: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate_files()
