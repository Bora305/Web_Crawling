import os

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK', '')

KEYWORDS = [
    "RTX",
    "노트북",
    "CPU",
    "그래픽카드",
    "GPU",
]

CHECK_INTERVAL = 5

SITES = {
    "quasarzone": {
        "url": "https://quasarzone.com/bbs/qb_jijang",
        "title_selector": "a.subject_link",
    },
    "coolenjoy": {
        "url": "https://coolenjoy.net/bbs/mart2",
        "title_selector": "a.na-subject",
    },
}

MAX_ALERTS_PER_RUN = 5
DEBUG_MODE = False
TIMEZONE = "Asia/Seoul"
