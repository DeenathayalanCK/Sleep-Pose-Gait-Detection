import logging
import os
import requests

logger = logging.getLogger(__name__)


def send_telegram_alert(message: str) -> None:
    """
    BUG FIX: telegram_alert.py was empty.
    Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env to enable.
    """
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.debug("Telegram not configured — skipping.")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
        resp.raise_for_status()
        logger.info("Telegram alert sent.")
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
