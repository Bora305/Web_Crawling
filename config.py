import os

# config.py - 모니터링 설정 파일
# 이 파일만 수정하면 됨!

# ===== 필수 설정 =====

# Discord 웹훅 URL (GitHub Secrets에서 로드됨)
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK', '')

# 감시할 키워드 (하나 이상 필수)
KEYWORDS = [
    "RTX",
    "노트북",
    "CPU",
    "그래픽카드",
    "GPU",
]

# 체크 간격 (분, 권장: 5~10분)
CHECK_INTERVAL = 5

# ===== 모니터링할 사이트 =====
# 💡 쿨엔조이: 모바일 버전(m.coolenjoy.net) 사용 (봇 차단 우회)
SITES = {
    "quasarzone": {
        "url": "https://quasarzone.com/bbs/qb_jijang",
        "title_selector": "a.subject_link",
    },
    "coolenjoy": {
        "url": "https://m.coolenjoy.net/bbs/mart2",  # ⭐ 모바일 버전 (봇 차단 우회)
        "title_selector": "a.na-subject",
    },
}

# ===== 선택 설정 =====

# 알림 보낼 최대 개수
MAX_ALERTS_PER_RUN = 5

# 상세 로깅
DEBUG_MODE = False

# 시간대
TIMEZONE = "Asia/Seoul"
