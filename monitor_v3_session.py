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
CHECK_INTERVAL = config.CHECK_INTERVAL
SITES = config.SITES
STATE_FILE = "monitored_posts.json"

USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
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
        print(f"⚠️  Discord 웹훅 미설정")
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
    except Exception as e:
        print(f"❌ 알림 전송 실패: {e}")
        return False

def get_session():
    """세션 객체 생성 (쿠키, 연결 풀 유지)"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    return session

def scrape_quasarzone():
    """퀘이사존 크롤링"""
    try:
        print("    🔄 퀘이사존 크롤링 중...")
        session = get_session()

        resp = session.get(
            SITES["quasarzone"]["url"],
            timeout=10,
            allow_redirects=True,
            verify=True,
        )
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        posts = []
        elements = soup.select("a.subject_link")

        if not elements:
            print("    ⚠️  선택자 미작동, 대체 검색 중...")
            elements = soup.find_all('a', limit=30)

        for elem in elements[:25]:
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
        print(f"    ❌ 퀘이사존 오류: {str(e)[:60]}")
        return "quasarzone", []

def scrape_coolenjoy():
    """쿨엔조이 크롤링 (재시도 로직 강화)"""

    for attempt in range(3):
        try:
            timeout = 8 - attempt  # 1차: 8초, 2차: 7초, 3차: 6초
            print(f"    🔄 쿨엔조이 크롤링 중 (시도 {attempt+1}/3, {timeout}초)...")

            session = get_session()

            # 1단계: 사이트 방문 (쿠키 받기)
            session.get("https://coolenjoy.net/", timeout=5, verify=True)

            # 2단계: 실제 페이지 요청
            resp = session.get(
                SITES["coolenjoy"]["url"],
                timeout=timeout,
                allow_redirects=True,
                verify=True,
            )
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            posts = []

            # 1순위: 특정 선택자
            elements = soup.select("a.na-subject")

            # 2순위: 다양한 클래스명 검색
            if len(elements) < 3:
                print("    ⚠️  선택자 미작동, 광범위 검색 중...")
                elements = soup.select("a[class*='subject']")

            # 3순위: 모든 링크 검색
            if len(elements) < 3:
                elements = soup.find_all('a', limit=50)

            for elem in elements[:30]:
                title = elem.get_text(strip=True)
                link = elem.get('href', '')

                if len(title) < 5 or not link:
                    continue

                if link.startswith('/'):
                    link = "https://coolenjoy.net" + link

                if any(p['link'] == link for p in posts):
                    continue

                posts.append({"title": title, "link": link, "site": "coolenjoy"})

            if len(posts) > 0:
                print(f"    ✅ 쿨엔조이: {len(posts)}개 수집")
                return "coolenjoy", posts
            else:
                if attempt < 2:
                    print(f"    ⏱️  0개 수집, 재시도 중...")
                    time.sleep(1)
                    continue

        except requests.Timeout:
            if attempt < 2:
                print(f"    ⏱️  타임아웃, 재시도 중...")
                time.sleep(1)
                continue
            else:
                print(f"    ❌ 쿨엔조이 타임아웃 (3회 재시도 실패)")
                return "coolenjoy", []
        except Exception as e:
            if attempt < 2:
                print(f"    ⚠️  오류 발생, 재시도 중: {str(e)[:40]}")
                time.sleep(1)
                continue
            else:
                print(f"    ❌ 쿨엔조이 오류: {str(e)[:60]}")
                return "coolenjoy", []

    print(f"    ❌ 쿨엔조이 3회 모두 실패")
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
    now = datetime.now().strftime("%m-%d %H:%M:%S")
    print(f"\n[{now}] ✅ 모니터링 완료")

if __name__ == "__main__":
    print("="*60)
    print("🌐 웹페이지 모니터링 프로그램 v3.2 (세션 유지 + 강화)")
    print("="*60)
    print(f"📌 감시 키워드: {', '.join(KEYWORDS)}")
    print(f"🌐 사이트 수: {len(SITES)}")
    print()

    monitor_task()
