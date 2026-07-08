import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import config
import time

DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL
KEYWORDS = config.KEYWORDS
CHECK_INTERVAL = config.CHECK_INTERVAL
SITES = config.SITES
STATE_FILE = "monitored_posts.json"

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
    """개선된 크롤링"""
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            print(f"    시도 {attempt + 1}/{max_retries}...")
            resp = requests.get(
                site_config["url"], 
                headers=headers, 
                timeout=30,
                allow_redirects=True
            )
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            posts = []
            
            # coolenjoy.net 특화 선택자
            elements = soup.select("a.na-subject")
            
            if len(elements) == 0:
                print(f"    ⚠️  na-subject 선택자 작동 안 함, 대체 선택자 시도...")
                elements = soup.find_all('a', limit=30)
            
            for elem in elements[:20]:
                title = elem.get_text(strip=True)
                link = elem.get('href', '')
                
                # 제목이 너무 짧으면 스킵
                if len(title) < 5:
                    continue
                
                # 링크가 없으면 스킵
                if not link:
                    continue
                
                # 상대 URL을 절대 URL로 변환
                if link.startswith('/'):
                    link = "https://coolenjoy.net" + link
                
                # 중복 제거
                if any(p['link'] == link for p in posts):
                    continue
                
                posts.append({"title": title, "link": link, "site": site_name})
            
            print(f"    ✅ 성공: {len(posts)}개 게시물 수집")
            return posts
            
        except requests.exceptions.Timeout:
            print(f"    ⏱️  타임아웃 (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                print(f"    ❌ 최종 실패")
                return []
                
        except Exception as e:
            print(f"    ❌ 오류: {str(e)[:50]}")
            return []

def check_keywords(title, keywords):
    for keyword in keywords:
        if keyword.lower() in title.lower():
            return keyword
    return None

def monitor_task():
    state = load_state()
    now = datetime.now().strftime("%m-%d %H:%M:%S")
    print(f"\n[{now}] 🔍 모니터링 시작...\n")
    
    alert_count = 0
    
    for site_name, site_config in SITES.items():
        print(f"  🌐 {site_name}")
        posts = scrape_site(site_name, site_config)
        
        for post in posts:
            post_id = f"{site_name}_{post['link']}"
            if post_id in state["posts"]:
                continue
            
            keyword = check_keywords(post["title"], KEYWORDS)
            if keyword:
                print(f"    🎯 발견: [{keyword}] {post['title'][:40]}...")
                
                if send_discord_alert(site_name, post["title"], post["link"], keyword):
                    print(f"       ✅ Discord 알림 전송됨")
                else:
                    print(f"       ⚠️  Discord 알림 전송 실패")
                
                state["posts"].append(post_id)
                alert_count += 1
    
    print(f"\n📊 결과:")
    if alert_count == 0:
        print(f"  새로운 키워드 항목 없음")
    else:
        print(f"  총 {alert_count}개 항목 감지 및 알림 전송!")
    
    save_state(state)
    print(f"\n[{now}] ✅ 모니터링 완료")

if __name__ == "__main__":
    print("="*60)
    print("🌐 웹페이지 모니터링 프로그램 v2 (coolenjoy 최적화)")
    print("="*60)
    print(f"📌 감시 키워드: {', '.join(KEYWORDS)}")
    print(f"⏲️  확인 간격: {CHECK_INTERVAL}분")
    print(f"🌐 사이트 수: {len(SITES)}")
    
    monitor_task()
