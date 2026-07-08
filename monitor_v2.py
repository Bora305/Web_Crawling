def scrape_site(site_name, site_config):
    """개선된 크롤링"""
    max_retries = 3  # 2 → 3으로 증가
    
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print(f"    시도 {attempt + 1}/{max_retries}...")
            resp = requests.get(
                site_config["url"], 
                headers=headers, 
                timeout=45,  # 30 → 45초
                allow_redirects=True
            )
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            posts = []
            elements = soup.select("a.na-subject")
            
            if len(elements) == 0:
                print(f"    ⚠️  na-subject 선택자 작동 안 함, 대체 선택자 시도...")
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
            
            print(f"    ✅ 성공: {len(posts)}개 게시물 수집")
            return posts
            
        except requests.exceptions.Timeout:
            print(f"    ⏱️  타임아웃 (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(3)  # 2 → 3초
                continue
            else:
                print(f"    ❌ 최종 실패 (coolenjoy 사이트 응답 문제)")
                return []
                
        except Exception as e:
            print(f"    ❌ 오류: {str(e)[:50]}")
            return []
