import time

import requests

from .config import TG_BOT_TOKEN, TG_CHAT_ID, logger


def send_telegram(text):
    """发送TG消息（自动分段，Markdown降级）"""
    if not TG_BOT_TOKEN:
        logger.info("\n[TG] No token, stdout:\n%s", text)
        return

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > 3800:
            chunks.append(current)
            current = line
        else:
            current += "\n" + line if current else line
    if current:
        chunks.append(current)

    for chunk in chunks:
        try:
            resp = requests.post(url, json={
                "chat_id": TG_CHAT_ID,
                "text": chunk,
                "parse_mode": "Markdown"
            }, timeout=10)
            if resp.status_code == 200:
                logger.info(f"[TG] Sent ✓ ({len(chunk)} chars)")
            else:
                resp2 = requests.post(url, json={
                    "chat_id": TG_CHAT_ID,
                    "text": chunk.replace("*", "").replace("_", ""),
                }, timeout=10)
                status = "✓" if resp2.status_code == 200 else "✗"
                logger.info(f"[TG] Sent plain ({status})")
        except Exception as e:
            logger.error(f"[TG] Error: {e}")
        time.sleep(0.5)
