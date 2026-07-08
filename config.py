import os

# config.py - 모니터링 설정 파일

# ===== 필수 설정 =====

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK', '')

KEYWORDS = [
    "RTX",
    "노트북",
    "CPU",
    "그래픽카드",
    "GPU",
]

CHECK_INTERVAL = 5

# ===== 모니터링할 사이트 =====
SITES = {
    "quasarzone": {
        "url": "https://quasarzone.com/bbs/qb_jijang",
        "title_selector": "a.subject_link",
    },
    "coolenjoy": {
        "url": "https://coolenjoy.net/bbs/mart2",  # ⭐ PC URL 유지 (세션 유지로 우회)
        "title_selector": "a.na-subject",
    },
}

# ===== 선택 설정 =====

MAX_ALERTS_PER_RUN = 5
DEBUG_MODE = False
TIMEZONE = "Asia/Seoul"
