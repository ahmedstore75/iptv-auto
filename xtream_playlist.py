import re
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
    প্লেলিস্টের নিজস্ব group-title এবং অন্যান্য অ্যাট্রিবিউট অপরিবর্তিত রেখে, 
    কমার পরের অংশ থেকে ঘড়ি (⏱️), ডট (·) বা অতিরিক্ত কমা ও স্পেস মুছে ফেলবে।
    """
    if ',' in extinf_line:
        parts = extinf_line.split(',', 1)
        attributes = parts[0]  # এখানে group-title, tvg-id, tvg-logo ইত্যাদি সব ঠিক থাকবে
        name_part = parts[1].strip()
        
        # নামের শুরুর ঘড়ি, ডট বা অতিরিক্ত কমা/স্পেস দূর করা
        cleaned_name = re.sub(r'^[⏱️·,\s]+', '', name_part)
        return f"{attributes},{cleaned_name}"
    return extinf_line

def process_playlist(content):
    lines = content.splitlines()
    processed_lines = []
    total_channels = 0
    
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U"):
            continue
            
        if line_str.startswith("#EXTINF:"):
            cleaned_line = clean_extinf_line(line_str)
            processed_lines.append(cleaned_line)
            total_channels += 1
        else:
            # #KODIPROP এবং স্ট্রিম লিংকসহ অন্যান্য সব লাইন হুবহু যুক্ত হবে
            processed_lines.append(line_str)

    print(f"✅ Total Processed Channels: {total_channels}")
    return "\n".join(processed_lines), total_channels

def fetch_and_generate():
    try:
        content = fetch_playlist_content(M3U_SOURCE_URL, retries=3, delay=5, timeout=60)
        filtered_content, total_saved = process_playlist(content)

        bd_tz = timezone(timedelta(hours=6))
        bd_time = datetime.now(bd_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        playlist_header = (
            f"#EXTM3U\n"
            f"# 📊 Total Channels: {total_saved}\n"
            f"# 📦 Complete Playlist with Original Groups & Cleaned Names\n"
            f"# ⏰ Updated time: {bd_time}\n"
        )
        
        final_m3u = playlist_header + filtered_content

        with open("playlist_x.m3u", "w", encoding="utf-8") as f:
            f.write(final_m3u)

        print(f"✅ playlist_x.m3u generated successfully at {bd_time} (Total Channels: {total_saved})")

    except Exception as e:
        print(f"❌ Error fetching playlist: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_generate()
