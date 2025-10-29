import asyncio
from pathlib import Path


LOGS_FOLDER = "logs/"
BODIES = "database/keep_bodies.txt"
WITHDRAW_REG = "database/withdraw_regular.txt"
P2P_REG = "database/p2p_regular.txt"
DEPOSIT_REG = "database/deposit_regular.txt"
TRASH_REG = "database/trash_regular.txt"

DEEPSEEK_API = "sk-0eaaf2ad59d547939fafd9953f03e83e"
BOT_TOKEN = "8156936879:AAGkopwiAUKqhoQ7WeWhVk88Mk6s5gbMffo"
OUTPUT_CHANNEL_TXT_ID = "-1002378196415"
OUTPUT_CHANNEL_LOGS_ID = "-1002378196415"
CHAT_TAGS = {}  # Оставьте пустым

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1flmM2s_TwcDMNwAKWYb_qMOqQC1uyzcY8TSkNxtXsQg/edit?usp=sharing"
GOOGLE_CREDENTIALS_FILE = (
    "second-project-428721-2911a79572d3.json"  # путь к  credentials
)
ADMIN_IDS = [7506300161, 7742837753]
SUPPLIERS = {
    -1002405948916: {"alias": "kent", "real": "cryptobrain"},
    -1003176580263: {"alias": "kent", "real": "cryptobrain"},
    -1002907257866: {"alias": "vicky", "real": "velvet"},
    -4987520181: {"alias": "milk", "real": "boss"},
    -1003020572173: {"alias": "whisky", "real": "winston"},
    -1003129902696: {"alias": "huyar", "real": "akhyar"},
    -1003175345101: {"alias": "smurf", "real": "smurf"},
}

DATA_DIR = Path("data")
COUNTERS_DIR = DATA_DIR / "daily_counters"
_counters_lock = asyncio.Lock()
