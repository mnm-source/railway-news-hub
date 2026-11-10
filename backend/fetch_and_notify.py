import os
import sqlite3
import hashlib
import feedparser
import requests
from datetime import datetime

# ค่าคงที่และ Token จาก GitHub Secrets
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")

# รายชื่อ RSS Feeds ตัวอย่าง
RSS_FEEDS = [
    {"name": "Thai PBS", "country": "Thailand", "url": "https://news.thaipbs.or.th/rss/news/general.xml"},
    {"name": "Bangkok Post", "country": "Thailand", "url": "https://www.bangkokpost.com/rss/data/topstories.xml"},
    {"name": "BBC World", "country": "International", "url": "http://feeds.bbci.co.uk/news/rss.xml"}
]

# คีย์เวิร์ดตรวจจับอุบัติเหตุร้ายแรง
ACCIDENT_KEYWORDS = ["รถไฟชน", "รถไฟตกราง", "รถไฟฟ้าขัดข้อง", "train derailment", "train crash", "rail accident"]

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles 
                 (id TEXT PRIMARY KEY, title TEXT, link TEXT, source TEXT, published_at TEXT, is_alerted INTEGER)''')
    conn.commit()
    conn.close()

def send_line_message(text):
    if not LINE_TOKEN or not USER_ID:
        print("Missing LINE Token or User ID")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    res = requests.post(url, headers=headers, json=payload)
    print(f"LINE Response: {res.status_code}")

def check_news():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    for feed_info in RSS_FEEDS:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:5]:
            title = entry.title
            link = entry.link
            news_id = hashlib.md5(link.encode()).hexdigest()

            c.execute("SELECT id FROM articles WHERE id = ?", (news_id,))
            if c.fetchone() is None:
                c.execute("INSERT INTO articles VALUES (?, ?, ?, ?, ?, 0)",
                          (news_id, title, link, feed_info["name"], str(datetime.now())))
                conn.commit()

                is_accident = any(kw.lower() in title.lower() for kw in ACCIDENT_KEYWORDS)
                if is_accident:
                    alert_msg = f"🚨 RAILWAY EMERGENCY ALERT\n\nแหล่งข่าว: {feed_info['name']}\nหัวข้อ: {title}\n\nอ่านข่าวเต็ม:\n{link}"
                    send_line_message(alert_msg)
                    c.execute("UPDATE articles SET is_alerted = 1 WHERE id = ?", (news_id,))
                    conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    send_line_message("🤖 สวัสดีครับ! ระบบ Railway News Hub เชื่อมต่อกับ LINE สำเร็จแล้ว")
    check_news()
