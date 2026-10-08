import logging
import smtplib
from email.mime.text import MIMEText

import requests as http

from scraper import Ad

logger = logging.getLogger(__name__)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_new_ads(ads: list[Ad], smtp_user: str, smtp_password: str, to: str) -> None:
    subject = f"[ikman-watcher] {len(ads)} new rental{'s' if len(ads) != 1 else ''} found"
    body_parts = []
    for ad in ads:
        body_parts.append(
            f"{ad.title}\n"
            f"  Price : Rs {ad.price:,}\n"
            f"  Beds  : {ad.beds}  Baths: {ad.baths}\n"
            f"  Type  : {ad.category}\n"
            f"  Link  : {ad.url}\n"
            f"  Posted: {ad.posted_time}\n"
        )
    body = "\n---\n".join(body_parts)
    _send_email(subject, body, smtp_user, smtp_password, to)


def send_error(message: str, smtp_user: str, smtp_password: str, to: str) -> None:
    subject = "[ikman-watcher] WARNING: watcher may be broken"
    body = f"Alert: {message}\n\nCheck GitHub Actions logs for details."
    _send_email(subject, body, smtp_user, smtp_password, to)


def send_telegram_new_ads(ads: list[Ad], bot_token: str, channel_id: str) -> None:
    for ad in ads:
        text = (
            f"<b>{_esc(ad.title)}</b>\n"
            f"Price: Rs {ad.price:,}\n"
            f"Beds: {ad.beds}  Baths: {ad.baths}\n"
            f"Type: {_esc(ad.category)}\n"
            f"Posted: {_esc(ad.posted_time)}\n"
            f"{ad.url}"
        )
        _send_telegram(text, bot_token, channel_id)


def send_telegram_error(message: str, bot_token: str, channel_id: str) -> None:
    text = f"WARNING: ikman-watcher may be broken\n\n{_esc(message)}\n\nCheck GitHub Actions logs."
    _send_telegram(text, bot_token, channel_id)


def _send_telegram(text: str, bot_token: str, channel_id: str) -> None:
    url = TELEGRAM_API.format(token=bot_token)
    resp = http.post(url, json={"chat_id": channel_id, "text": text, "parse_mode": "HTML"}, timeout=15)
    resp.raise_for_status()
    logger.info("Telegram message sent to %s", channel_id)


def _esc(text: str) -> str:
    for ch in ("&", "<", ">"):
        text = text.replace(ch, {"&": "&amp;", "<": "&lt;", ">": "&gt;"}[ch])
    return text


def _send_email(subject: str, body: str, smtp_user: str, smtp_password: str, to: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to, msg.as_string())
    logger.info("Email sent: %s", subject)
