import os

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK', '')

KEYWORDS = [
    "13900",
    "13900K",
    "13900KF",
    "13900F",
    "14900",
    "14900F",
    "14900KF",
    "14900K",
    "13700",
    "13700F",
    "13700KF",
    "13700K",
    "14700",
    "14700F",
    "14700KF",
    "14700K",
    "265K",
    "285K",
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
