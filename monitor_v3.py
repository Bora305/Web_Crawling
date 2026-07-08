import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import config
from concurrent.futures import ThreadPoolExecutor, as_completed

DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL
KEYWORDS = config.KEYWORDS
CHECK_INTERVAL = config.CHECK_INTERVAL
SITES = config.SITES
STATE_FILE = "monitored_posts.json"

# 다양한 User-Agent 목록 (차단 우회)
USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/91.0.4472.120',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0',
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

def scrape_quasarzone():
    """퀘이사존 크롤링"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        print("    🔄 퀘이사존 크롤링 중...")

        resp = requests.get(
            SITES["quasarzone"]["url"],
            headers=headers,
            timeout=8,
        )
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        posts = []
        elements = soup.select("a.subject_link")

        if not elements:
            print("    ⚠️  선택자 미작동, 대체 검색 중...")
            elements = soup.find_all('a', limit=30)

        for elem in elements[:20]:
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
        print(f"    ❌ 퀘이사존 오류: {str(e)[:50]}")
        return "quasarzone", []

def scrape_coolenjoy():
    """쿨엔조이 크롤링 (재시도 로직)"""
    import random

    for attempt in range(3):
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'ko-KR,ko;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://coolenjoy.net/',
            }

            timeout = 6 - (attempt * 2)  # 1차: 6초, 2차: 4초, 3차: 2초
            print(f"    🔄 쿨엔조이 크롤링 중 (시도 {attempt+1}/3, {timeout}초 타임아웃)...")

            resp = requests.get(
                SITES["coolenjoy"]["url"],
                headers=headers,
                timeout=timeout,
            )
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            posts = []
            elements = soup.select("a.na-subject")

            if not elements:
                print("    ⚠️  선택자 미작동, 모든 a 태그 검색 중...")
                elements = soup.find_all('a', limit=40)

            for elem in elements[:20]:
                title = elem.get_text(strip=True)
                link = elem.get('href', '')

                if len(title) < 5 or not link:
                    continue

                if link.startswith('/'):
                    link = "https://coolenjoy.net" + link

                if any(p['link'] == link for p in posts):
                    continue

                posts.append({"title": title, "link": link, "site": "coolenjoy"})

            print(f"    ✅ 쿨엔조이: {len(posts)}개 수집")
            return "coolenjoy", posts

        except requests.Timeout:
            if attempt < 2:
                print(f"    ⏱️  타임아웃, 재시도 중...")
                continue
            else:
                print(f"    ❌ 쿨엔조이 타임아웃 (3회 재시도 실패)")
                return "coolenjoy", []
        except Exception as e:
            print(f"    ❌ 쿨엔조이 오류: {str(e)[:50]}")
            return "coolenjoy", []

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

    # 병렬 처리로 속도 최적화
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}

        if "quasarzone" in SITES:
            futures[executor.submit(scrape_quasarzone)] = "quasarzone"

        if "coolenjoy" in SITES:
            futures[executor.submit(scrape_coolenjoy)] = "coolenjoy"

        for future in as_completed(futures):
            site_name, posts = future.result()
            all_results[site_name] = posts

    # 결과 처리
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
    print("🌐 웹페이지 모니터링 프로그램 v3 (최적화)")
    print("="*60)
    print(f"📌 감시 키워드: {', '.join(KEYWORDS)}")
    print(f"🌐 사이트 수: {len(SITES)}")
    print()

    monitor_task()
