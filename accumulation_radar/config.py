import logging
import os
from pathlib import Path

# === 加载 .env ===
env_file = Path(__file__).resolve().parent.parent / ".env.oi"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# === 日志 ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# === Telegram ===
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")

# === Email (QQ邮箱) ===
EMAIL_ENABLE = os.getenv("EMAIL_ENABLE", "false").lower() == "true"
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = [e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",") if e.strip()]
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.qq.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))

# === API ===
FAPI = "https://fapi.binance.com"
DB_PATH = Path(__file__).resolve().parent.parent / "accumulation.db"

# === 收筹标的池参数 ===
MIN_SIDEWAYS_DAYS = 45
MAX_RANGE_PCT = 80
MAX_AVG_VOL_USD = 20_000_000
MIN_DATA_DAYS = 50

# === OI异动参数 ===
MIN_OI_DELTA_PCT = 3.0
MIN_OI_USD = 2_000_000

# === 放量突破参数 ===
VOL_BREAKOUT_MULT = 3.0
