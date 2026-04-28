import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DB
DB_PATH = os.path.join(BASE_DIR, "data", "worklog.db")

# 앱 설정
APP_HOST = "127.0.0.1"
APP_PORT = 8080
SECRET_KEY = "change-this-in-production"

# 알림 시각 (24시간제)
MORNING_BRIEF_HOUR = 9    # 오전 9시
EVENING_CHECK_HOUR = 17   # 오후 5시 30분
EVENING_CHECK_MIN  = 30

# 방치 Task 기준 (일)
STALE_TASK_DAYS = 7

# 텔레그램 (나중에 채우기)
TELEGRAM_TOKEN   = ""
TELEGRAM_CHAT_ID = ""
