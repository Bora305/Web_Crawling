import os

# config.py - 모니터링 설정 파일
# 이 파일만 수정하면 됨!

# ===== 필수 설정 =====

# Discord 웹훅 URL (필수!)
# Discord 서버 → 채널 우클릭 → 웹훅 → URL 복사
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK', '')

# 감시할 키워드 (하나 이상 필수)
KEYWORDS = [
    "RTX",
    "노트북",
    "CPU",
    "그래픽카드",
]

# 체크 간격 (분, 권장: 5~10분)
CHECK_INTERVAL = 5

# ===== 모니터링할 사이트 =====
SITES = {
    "quasarzone": {
        "url": "https://quasarzone.com/bbs/qb_jijang",
        "title_selector": "a.subject_link",
    },
    "coolenjoy": {
        "url": "https://coolenjoy.net/bbs/mart2",
        "title_selector": "a.title",
    },
    # 추가 예시:
    # "naver_cafe": {
    #     "url": "https://cafe.naver.com/ArticleList.nhn?search.clubid=...",
    #     "title_selector": "a.article",
    # }
}

# ===== 선택 설정 =====

# 알림 보낼 최대 개수 (너무 많으면 스팸처럼 느껴질 수 있음)
MAX_ALERTS_PER_RUN = 5

# 상세 로깅 (True면 더 많은 정보 출력)
DEBUG_MODE = False

# 시간대 (한국: "Asia/Seoul")
TIMEZONE = "Asia/Seoul"
