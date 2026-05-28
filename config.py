import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8272437053:AAFaSUtQmFBqu3hGr2CC_nU3W_egEqX-e3w")
OWNER_IDS = [int(x.strip()) for x in os.getenv("OWNER_IDS", "5762701937,8119946836").split(",") if x.strip()]

LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")
FORCE_JOIN_CHANNELS = [x.strip() for x in os.getenv("FORCE_JOIN_CHANNELS", "").split(",") if x.strip()]
FORCE_JOIN_LINKS = [x.strip() for x in os.getenv("FORCE_JOIN_LINKS", "").split(",") if x.strip()]

MINI_APP_URL = os.getenv("MINI_APP_URL", "")

BIN_API_URL = "https://bindb.rythampkhandelwal.workers.dev/bin/{bin}"

BOT_NAME = "DAMXD AUTO HITTER"
BOT_USERNAME = "@newthingsneverbot"
SUPPORT_USERNAME = "@DAMXD89"
OWNER_USERNAME = "@DAMXD89"

FREE_DAILY_LIMIT = 10

# System-level proxy pool — used when a user has no personal proxy set.
# Paid users should add their own proxy; free users rotate through these.
SYSTEM_PROXIES = [
    "14.143.222.113:57718",
    "104.194.144.249:80",
    "176.111.37.216:39811",
    "2.26.87.216:1080",
    "174.138.174.138:8254",
    "113.192.12.24:8080",
    "45.13.237.201:3128",
    "80.90.183.221:3128",
    "85.192.29.60:3128",
    "38.194.246.34:999",
    "89.22.225.204:8080",
    "148.230.4.241:999",
    "182.53.202.208:8080",
    "157.230.28.51:1981",
    "154.223.188.202:1194",
]

PLAN_PRICES = {
    "1d":    {"days": 1,    "label": "1 Day"},
    "3d":    {"days": 3,    "label": "3 Days"},
    "7d":    {"days": 7,    "label": "7 Days"},
    "14d":   {"days": 14,   "label": "14 Days"},
    "30d":   {"days": 30,   "label": "30 Days"},
    "60d":   {"days": 60,   "label": "60 Days"},
    "90d":   {"days": 90,   "label": "90 Days"},
    "180d":  {"days": 180,  "label": "180 Days"},
    "365d":  {"days": 365,  "label": "365 Days"},
}

DB_PATH = os.getenv("DB_PATH", "")

# MongoDB Configuration
MONGO_URL = os.getenv("MONGO_URL", "")
DB_NAME = os.getenv("DB_NAME", "damxd89_bot")
