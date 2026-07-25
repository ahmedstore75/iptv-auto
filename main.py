import os

# আপনার পছন্দমতো চ্যানেলের নাম, লোগো এবং লাইভ স্ট্রিম লিংক বসান
channels = [
    {
        "name": "BTV World",
        "logo": "https://ssl.bd.com/sites/default/files/btv.png",
        "group": "BANGLA",
        "url": "https://example.com/live/btv/index.m3u8"
    },
    {
        "name": "Channel 24",
        "logo": "https://dl.dropbox.com/s/channel24.png",
        "group": "BANGLA",
        "url": "https://example.com/live/channel24/index.m3u8"
    }
]

# M3U ফাইলের ফরম্যাট তৈরি
m3u_content = "#EXTM3U\n"
for ch in channels:
    m3u_content += f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}\n'
    m3u_content += f'{ch["url"]}\n'

# ফাইল হিসেবে সেভ করা
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_content)

print("Playlist updated!")
