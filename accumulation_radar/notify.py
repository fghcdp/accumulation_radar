import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

from .config import (
    TG_BOT_TOKEN, TG_CHAT_ID,
    EMAIL_ENABLE, EMAIL_SENDER, EMAIL_PASSWORD,
    EMAIL_RECIPIENTS, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT,
    logger
)

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

def send_email(text, subject="庄家收筹雷达 - 策略评分报告"):
    """发送QQ邮件"""
    if not EMAIL_ENABLE:
        logger.info("[Email] Disabled, skipping")
        return

    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENTS:
        logger.warning("[Email] Missing credentials (sender, password, or recipients)")
        return

    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = ', '.join(EMAIL_RECIPIENTS)

        # 纯文本版本
        part1 = MIMEText(text, 'plain', _charset='utf-8')

        # HTML版本（美化格式）
        html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                    .header {{ color: #e74c3c; font-weight: bold; font-size: 18px; margin: 10px 0; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; }}
                    pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 13px; line-height: 1.5; }}
                    .footer {{ color: #999; font-size: 12px; margin-top: 20px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">🏦 {subject}</div>
                    <pre>{text}</pre>
                    <div class="footer">此报告由自动化脚本生成 | {subject}</div>
                </div>
            </body>
        </html>
        """
        part2 = MIMEText(html, 'html', _charset='utf-8')

        msg.attach(part1)
        msg.attach(part2)

        # 发送邮件（QQ邮箱用SMTP）
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, timeout=10) as server:
            server.starttls()  # 启用TLS加密
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())

        logger.info(f"[Email] Sent ✓ to {', '.join(EMAIL_RECIPIENTS)}")

    except smtplib.SMTPAuthenticationError:
        logger.error("[Email] Authentication failed - check QQ email and password")
    except smtplib.SMTPException as e:
        logger.error(f"[Email] SMTP Error: {e}")
    except Exception as e:
        logger.error(f"[Email] Error: {e}")

def notify(text, subject="庄家收筹雷达报告"):
    """统一推送接口（同时发送到TG和邮箱）"""
    send_telegram(text)
    send_email(text, subject)
