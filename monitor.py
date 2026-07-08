import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json
import os
from pathlib import Path

# ===== 설정 영역 =====
KEYWORDS = ["RTX", "노트북", "CPU"]  # 모니터링할 키워드 리스트
CHECK_INTERVAL = 5  # 몇 분마다 확인할지 (최소 5분 권장)
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"  # Discord 웹훅 URL

SITES = {
    "quasarzone": {
        "url": "https://quasarzone.com/bbs/qb_jijang",
        "title_selector": "a.subject_link",  # 제목 선택자
    },
    "coolenjoy": {
        "url": "https://coolenjoy.net/bbs/mart2",
        "title_selector": "a.title",  # 제목 선택자
    }
}

# 저장 파일
STATE_FILE = "monitored_posts.json"

# ===== 함수 정의 =====

def load_state():
    """이전에 감지한 게시물 로드"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"posts": []}

def save_state(state):
    """감지한 게시물 저장"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_discord_alert(site_name, title, url, keyword):
    """Discord로 알림 전송"""
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        print(f"⚠️  Discord 웹훅 URL이 설정되지 않았습니다")
        return

    message = {
        "content": f"🔔 **새 게시물 감지!**",
        "embeds": [{
            "title": title,
            "url": url,
            "description": f"**키워드:** {keyword}\n**사이트:** {site_name}",
            "color": 16711680,  # 빨강
            "timestamp": datetime.now().isoformat()
        }]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        if response.status_code == 204:
            print(f"✅ Discord 알림 전송 성공: {title}")
        else:
            print(f"❌ Discord 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 알림 전송 중 오류: {e}")

def scrape_site(site_name, site_config):
    """사이트에서 게시물 수집"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(site_config["url"], headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        posts = []
        elements = soup.select(site_config["title_selector"])[:10]  # 최상단 10개만

        for elem in elements:
            title = elem.get_text(strip=True)
            link = elem.get('href', '')

            # 상대 URL 절대 URL로 변환
            if link.startswith('/'):
                link = site_config["url"].split('/bbs')[0] + link

            if title:
                posts.append({
                    "title": title,
                    "link": link,
                    "site": site_name
                })

        return posts
    except Exception as e:
        print(f"❌ {site_name} 크롤링 오류: {e}")
        return []

def check_keywords(title, keywords):
    """제목에 키워드가 포함되어 있는지 확인"""
    title_lower = title.lower()
    for keyword in keywords:
        if keyword.lower() in title_lower:
            return keyword
    return None

def monitor_task():
    """모니터링 메인 작업"""
    state = load_state()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] 🔍 모니터링 시작...")

    for site_name, site_config in SITES.items():
        posts = scrape_site(site_name, site_config)

        for post in posts:
            post_id = f"{site_name}_{post['link']}"

            # 이미 감지한 게시물인지 확인
            if post_id in state["posts"]:
                continue

            # 키워드 확인
            matched_keyword = check_keywords(post["title"], KEYWORDS)
            if matched_keyword:
                print(f"\n🎯 새 게시물 발견!")
                print(f"   사이트: {site_name}")
                print(f"   제목: {post['title']}")
                print(f"   키워드: {matched_keyword}")

                # Discord 알림 전송
                send_discord_alert(
                    site_name,
                    post["title"],
                    post["link"],
                    matched_keyword
                )

                # 상태 저장
                state["posts"].append(post_id)
                save_state(state)

    print(f"[{timestamp}] ✅ 모니터링 완료")

def start_scheduler():
    """스케줄러 시작"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_task, 'interval', minutes=CHECK_INTERVAL)
    scheduler.start()
    print(f"🚀 모니터링 시작됨 ({CHECK_INTERVAL}분 간격)")
    print(f"📌 감시 키워드: {', '.join(KEYWORDS)}")
    print("   (종료: Ctrl+C)")

    try:
        while True:
            pass  # 계속 실행
    except KeyboardInterrupt:
        print("\n⛔ 모니터링 종료")
        scheduler.shutdown()

# ===== 실행 =====
if __name__ == "__main__":
    print("="*60)
    print("🌐 웹페이지 키워드 모니터링 프로그램")
    print("="*60)

    # 첫 번째 실행
    print(f"\n⏳ 첫 번째 모니터링 실행 중...")
    monitor_task()

    # 스케줄러 시작
    print(f"\n⏲️  백그라운드 스케줄러 시작...")
    start_scheduler()
