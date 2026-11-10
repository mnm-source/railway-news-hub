import os
import sqlite3
import hashlib
import feedparser
import requests
import json
from datetime import datetime

LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")

# เปลี่ยนมาใช้แหล่งข่าวสายรถไฟฟ้า / คมนาคม และสำนักข่าวที่มีข่าวรางเด่นชัด
RSS_FEEDS = [
    {"name": "Railway Gazette", "country": "International", "url": "https://www.railwaygazette.com/rss.xml"},
    {"name": "Global Railway Review", "country": "International", "url": "https://www.globalrailwayreview.com/feed/"},
    {"name": "Prachachat (Transport)", "country": "Thailand", "url": "https://www.prachachat.net/ic-motoring/feed"}, # ข่าวคมนาคม ขนส่ง รถไฟฟ้าไทย
    {"name": "Thai PBS (General)", "country": "Thailand", "url": "https://news.thaipbs.or.th/rss/news/general.xml"}
]

# คีย์เวิร์ดบังคับ (ต้องมีคำเหล่านี้ในหัวข้อข่าว ถึงจะดึงมาแสดง)
RAILWAY_KEYWORDS = [
    "รถไฟ", "รถไฟฟ้า", "mrt", "bts", "แอร์พอร์ตลิงก์", "รฟฟ.", "รฟม.", "รฟท.", 
    "รถไฟใต้ดิน", "รถไฟความเร็วสูง", "ชานชาลา", "ระบบราง", "สายสี", 
    "train", "railway", "metro", "subway", "skytrain", "rail", "locomotive", "transit"
]

ACCIDENT_KEYWORDS = ["รถไฟชน", "รถไฟตกราง", "รถไฟฟ้าขัดข้อง", "train derailment", "train crash", "rail accident"]

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles 
                 (id TEXT PRIMARY KEY, title TEXT, link TEXT, source TEXT, country TEXT, published_at TEXT, is_alerted INTEGER)''')
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
    all_articles = []

    for feed_info in RSS_FEEDS:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            
            # ตรวจสอบความเกี่ยวข้องกับรถไฟฟ้า
            is_railway_news = any(kw.lower() in title.lower() for kw in RAILWAY_KEYWORDS)
            
            if not is_railway_news:
                continue

            news_id = hashlib.md5(link.encode()).hexdigest()
            published = str(datetime.now().strftime("%Y-%m-%d %H:%M"))

            c.execute("SELECT id FROM articles WHERE id = ?", (news_id,))
            if c.fetchone() is None:
                c.execute("INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, 0)",
                          (news_id, title, link, feed_info["name"], feed_info["country"], published))
                conn.commit()

                is_accident = any(kw.lower() in title.lower() for kw in ACCIDENT_KEYWORDS)
                if is_accident:
                    alert_msg = f"🚨 RAILWAY EMERGENCY ALERT\n\nแหล่งข่าว: {feed_info['name']}\nหัวข้อ: {title}\n\nอ่านข่าวเต็ม:\n{link}"
                    send_line_message(alert_msg)
                    c.execute("UPDATE articles SET is_alerted = 1 WHERE id = ?", (news_id,))
                    conn.commit()

            all_articles.append({
                "id": news_id,
                "title": title,
                "link": link,
                "source": feed_info["name"],
                "country": feed_info["country"],
                "published_at": published,
                "is_accident": any(kw.lower() in title.lower() for kw in ACCIDENT_KEYWORDS)
            })

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    conn.close()

if __name__ == "__main__":
    init_db()
    check_news()
