import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import config
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL
KEYWORDS = config.KEYWORDS
SITES = config.SITES
STATE_FILE = "monitored_posts.json"

USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/119.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0',
]

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
        return False

    message = {
        "content": f"🔔 **{site_name}에서 새 게시물!**",
        "embeds": [{
            "title": title[:256],
            "url": url,
            "description": f"**키워드:** {keyword}",
            "color": 16711680,
            "timestamp": datetime.now().isoformat()
        }]
    }

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=message, timeout=5)
        return resp.status_code == 204
    except:
        return False

def get_session():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # ⭐ 추가
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    })
    return session

def scrape_quasarzone():
    try:
        print("    🔄 퀘이사존 크롤링 중...")
        session = get_session()

        resp = session.get(
            SITES["quasarzone"]["url"],
            timeout=10,
            allow_redirects=True,
        )
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        posts = []
        elements = soup.select("a.subject_link")

        if not elements:
            elements = soup.find_all('a', limit=40)

        for elem in elements[:30]:
            title = elem.get_text(strip=True)
            link = elem.get('href', '')

            if len(title) < 5 or not link:
                continue

            if link.startswith('/'):
                link = "https://quasarzone.com" + link

            if any(p['link'] == link for p in posts):
                continue

            posts.append({"title": title, "link": link, "site": "quasarzone"})

        print(f"    ✅ 퀘이사존: {len(posts)}개 수집")
        return "quasarzone", posts

    except Exception as e:
        print(f"    ❌ 퀘이사존 오류: {str(e)[:40]}")
        return "quasarzone", []

def scrape_coolenjoy():
    """쿨엔조이 크롤링 (HTML 파싱 - B 방식)"""
    try:
        print("    🔄 쿨엔조이 크롤링 중...")
        session = get_session()
        
        # 타임아웃 증가 + SSL 검증 비활성화
        resp = session.get(
            SITES["coolenjoy"]["url"],
            timeout=15,              # ⭐ 10 → 15초로 증가
            allow_redirects=True,
            verify=False             # ⭐ SSL 검증 비활성화
        )
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        posts = []
        
        # HTML 텍스트 추출
        full_text = soup.get_text(separator='\n')
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        
        # 게시물 찾기: "제목" + "가격" 패턴
        i = 0
        while i < len(lines) - 1:
            current = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            
            # 가격 판별: "숫자...원" 형식
            is_price = (
                '원' in next_line and 
                any(c.isdigit() for c in next_line) and
                len(next_line) < 50
            )
            
            # 제목 판별
            is_title = (
                len(current) > 5 and 
                len(current) < 200 and
                not any(c.isdigit() for c in current[-5:])
            )
            
            if is_title and is_price:
                title = current
                price = next_line
                
                # 제외 단어
                if any(skip in title for skip in ['아이디로 검색', '건의함', '로그인', '글쓴이', '페이지', '포인트']):
                    i += 1
                    continue
                
                # 중복 제거
                if not any(p['title'] == title for p in posts):
                    posts.append({
                        "title": title,
                        "link": SITES["coolenjoy"]["url"],
                        "site": "coolenjoy",
                        "price": price
                    })
                
                i += 2
                continue
            
            i += 1

        print(f"    ✅ 쿨엔조이: {len(posts)}개 수집")
        return "coolenjoy", posts

    except Exception as e:
        print(f"    ⚠️  쿨엔조이 재시도 중...")
        # 재시도 (2초 대기)
        time.sleep(2)
        try:
            session = get_session()
            resp = session.get(
                SITES["coolenjoy"]["url"],
                timeout=20,
                allow_redirects=True,
                verify=False
            )
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            posts = []
            
            full_text = soup.get_text(separator='\n')
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            i = 0
            while i < len(lines) - 1:
                current = lines[i]
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                
                is_price = ('원' in next_line and any(c.isdigit() for c in next_line) and len(next_line) < 50)
                is_title = (len(current) > 5 and len(current) < 200 and not any(c.isdigit() for c in current[-5:]))
                
                if is_title and is_price:
                    title = current
                    if any(skip in title for skip in ['아이디로 검색', '건의함', '로그인', '글쓴이', '페이지', '포인트']):
                        i += 1
                        continue
                    
                    if not any(p['title'] == title for p in posts):
                        posts.append({"title": title, "link": SITES["coolenjoy"]["url"], "site": "coolenjoy"})
                    i += 2
                    continue
                
                i += 1
            
            print(f"    ✅ 쿨엔조이: {len(posts)}개 수집 (재시도)")
            return "coolenjoy", posts
        except:
            print(f"    ❌ 쿨엔조이 실패")
            return "coolenjoy", []


def check_keywords(title, keywords):
    for keyword in keywords:
        if keyword.lower() in title.lower():
            return keyword
    return None

def monitor_task():
    state = load_state()
    now = datetime.now().strftime("%m-%d %H:%M:%S")
    print(f"\n[{now}] 🔍 모니터링 시작\n")

    alert_count = 0
    all_results = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}

        if "quasarzone" in SITES:
            futures[executor.submit(scrape_quasarzone)] = "quasarzone"

        if "coolenjoy" in SITES:
            futures[executor.submit(scrape_coolenjoy)] = "coolenjoy"

        for future in as_completed(futures):
            site_name, posts = future.result()
            all_results[site_name] = posts

    for site_name, posts in all_results.items():
        print(f"\n  🌐 {site_name} 결과 처리 중...")

        for post in posts:
            post_id = f"{site_name}_{post['link']}"
            if post_id in state["posts"]:
                continue

            keyword = check_keywords(post["title"], KEYWORDS)
            if keyword:
                print(f"    🎯 발견: [{keyword}] {post['title'][:40]}...")

                if send_discord_alert(site_name, post["title"], post["link"], keyword):
                    print(f"       ✅ 알림 전송")

                state["posts"].append(post_id)
                alert_count += 1

    print(f"\n📊 결과: {alert_count}개 감지")

    save_state(state)
    now = datetime.now().strftime("%m-%d %H:%M:%S")
    print(f"[{now}] ✅ 완료")

if __name__ == "__main__":
    print("="*60)
    print("🌐 모니터링 v3.4 (HTML 파싱)")
    print("="*60)
    print(f"키워드: {', '.join(KEYWORDS)}")
    print()

    monitor_task()
