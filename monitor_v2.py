import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import config
import asyncio
from playwright.async_api import async_playwright

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

def scrape_site_requests(site_name, site_config):
    """일반 requests 크롤링 (quasarzone용)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        print(f"    {site_name} 크롤링 중...")
        resp = requests.get(
            site_config["url"], 
            headers=headers, 
            timeout=10,
        )
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        posts = []
        
        # 선택자가 없으면 모든 a 태그 찾기
        if "title_selector" in site_config:
            elements = soup.select(site_config["title_selector"])
        else:
            elements = soup.find_all('a', limit=30)
        
        if len(elements) == 0:
            print(f"    ⚠️  선택자 미작동, 대체 검색 중...")
            elements = soup.find_all('a', limit=30)
        
        for elem in elements[:20]:
            title = elem.get_text(strip=True)
            link = elem.get('href', '')
            
            if len(title) < 5:
                continue
            
            if not link:
                continue
            
            if link.startswith('/'):
                base_url = site_config["url"].split('/bbs')[0]
                link = base_url + link
            
            if any(p['link'] == link for p in posts):
                continue
            
            posts.append({"title": title, "link": link, "site": site_name})
        
        print(f"    ✅ {site_name}: {len(posts)}개 게시물 수집")
        return site_name, posts
        
    except Exception as e:
        print(f"    ❌ {site_name} 오류: {str(e)[:50]}")
        return site_name, []

async def scrape_site_playwright(site_name, site_config):
    """Playwright를 사용한 크롤링 (coolenjoy용)"""
    try:
        print(f"    {site_name} 크롤링 중 (Playwright)...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # 타임아웃 8초로 단축
            try:
                await page.goto(site_config["url"], timeout=8000, wait_until="domcontentloaded")
            except:
                print(f"    ⚠️  페이지 로드 타임아웃, 부분 데이터로 계속...")
            
            # 1초만 대기
            await page.wait_for_timeout(1000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            posts = []
            elements = soup.select("a.na-subject")
            
            if len(elements) == 0:
                print(f"    ⚠️  선택자 미작동, 모든 링크 검색 중...")
                elements = soup.find_all('a', limit=30)
            
            for elem in elements[:20]:
                title = elem.get_text(strip=True)
                link = elem.get('href', '')
                
                if len(title) < 5:
                    continue
                
                if not link:
                    continue
                
                if link.startswith('/'):
                    link = "https://coolenjoy.net" + link
                
                if any(p['link'] == link for p in posts):
                    continue
                
                posts.append({"title": title, "link": link, "site": site_name})
            
            await browser.close()
            
            print(f"    ✅ {site_name}: {len(posts)}개 게시물 수집")
            return site_name, posts
            
    except Exception as e:
        print(f"    ❌ {site_name} 오류: {str(e)[:50]}")
        return site_name, []

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
    all_results = {}
    
    # quasarzone: requests 사용
    if "quasarzone" in SITES:
        site_name, posts = scrape_site_requests("quasarzone", SITES["quasarzone"])
        all_results[site_name] = posts
    
    # coolenjoy: Playwright 사용
    if "coolenjoy" in SITES:
        site_name, posts = asyncio.run(scrape_site_playwright("coolenjoy", SITES["coolenjoy"]))
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
    print(f"\n[{now}] ✅ 모니터링 완료")

if __name__ == "__main__":
    print("="*60)
    print("🌐 웹페이지 모니터링 프로그램 v2 (Playwright 적용)")
    print("="*60)
    print(f"📌 감시 키워드: {', '.join(KEYWORDS)}")
    
    print(f"⏲️  확인 간격: {CHECK_INTERVAL}분")
    
    print(f"🌐 사이트 수: {len(SITES)}")
    
    monitor_task()
