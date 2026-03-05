import smtplib
import logging
import os
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email_alert(subject: str, body: str) -> None:
    """
    BUG FIX: email_alert.py was empty.
    Reads SMTP config from environment variables.
    Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_TO in .env.
    """
    host  = os.getenv("SMTP_HOST")
    port  = int(os.getenv("SMTP_PORT", "587"))
    user  = os.getenv("SMTP_USER")
    passwd = os.getenv("SMTP_PASS")
    to    = os.getenv("ALERT_TO")

    if not all([host, user, passwd, to]):
        logger.debug("Email alert not configured — skipping.")
        return

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = user
        msg["To"]      = to

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, passwd)
            server.sendmail(user, [to], msg.as_string())

        logger.info(f"Email alert sent to {to}")
    except Exception as e:
        logger.error(f"Email alert failed: {e}")
