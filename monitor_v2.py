import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import config

# ===== 설정 로드 =====
DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL
KEYWORDS = config.KEYWORDS
CHECK_INTERVAL = config.CHECK_INTERVAL
SITES = config.SITES
STATE_FILE = "monitored_posts.json"

# ===== 함수 =====

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"posts": []}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_discord_alert(site_name, title, url, keyword):
    if not DISCORD_WEBHOOK_URL:
        print(f"⚠️  Discord 웹훅이 설정되지 않았습니다.")
        return False
    
    message = {
        "content": f"🔔 **{site_name}에서 새 게시물 발견!**",
        "embeds": [{
            "title": title[:256],
            "url": url,
            "description": f"**키워드 매치:** {keyword}",
            "color": 16711680,
            "timestamp": datetime.now().isoformat()
        }]
    }
    
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=message, timeout=5)
        return resp.status_code == 204
    except Exception as e:
        print(f"❌ 알림 전송 실패: {e}")
        return False

def scrape_site(site_name, site_config):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(site_config["url"], headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        posts = []
        for elem in soup.select(site_config["title_selector"])[:15]:
            title = elem.get_text(strip=True)
            link = elem.get('href', '')
            
            if link.startswith('/'):
                base = site_config["url"].split('/bbs')[0] if '/bbs' in site_config["url"] else site_config["url"]
                link = base + link
            
            if title and link:
                posts.append({"title": title, "link": link, "site": site_name})
        
        return posts
    except Exception as e:
        print(f"❌ {site_name} 오류: {e}")
        return []

def check_keywords(title, keywords):
    for keyword in keywords:
        if keyword.lower() in title.lower():
            return keyword
    return None

def monitor_task():
    state = load_state()
    now = datetime.now().strftime("%m-%d %H:%M:%S")
    print(f"\n[{now}] 🔍 모니터링 시작...")
    
    alert_count = 0
    
    for site_name, site_config in SITES.items():
        posts = scrape_site(site_name, site_config)
        
        for post in posts:
            post_id = f"{site_name}_{post['link']}"
            if post_id in state["posts"]:
                continue
            
            keyword = check_keywords(post["title"], KEYWORDS)
            if keyword:
                print(f"  🎯 발견: [{keyword}] {post['title'][:50]}")
                
                if send_discord_alert(site_name, post["title"], post["link"], keyword):
                    print(f"     ✅ 알림 전송됨")
                else:
                    print(f"     ❌ 알림 전송 실패")
                
                state["posts"].append(post_id)
                alert_count += 1
    
    if alert_count == 0:
        print("   새로운 항목 없음")
    else:
        print(f"   총 {alert_count}개 항목 감지")
    
    save_state(state)
    print(f"[{now}] ✅ 모니터링 완료")

if __name__ == "__main__":
    print("="*60)
    print("🌐 웹페이지 모니터링 프로그램 v2")
    print("="*60)
    print(f"📌 감시 키워드: {', '.join(KEYWORDS)}")
    print(f"⏲️  확인 간격: {CHECK_INTERVAL}분")
    print(f"🌐 사이트 수: {len(SITES)}")
    
    # GitHub Actions에서 한 번만 실행
    monitor_task()
