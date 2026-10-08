import logging
import smtplib
from email.mime.text import MIMEText
from scraper import Ad

logger = logging.getLogger(__name__)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


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
    _send(subject, body, smtp_user, smtp_password, to)


def send_error(message: str, smtp_user: str, smtp_password: str, to: str) -> None:
    subject = "[ikman-watcher] WARNING: watcher may be broken"
    body = f"Alert: {message}\n\nCheck GitHub Actions logs for details."
    _send(subject, body, smtp_user, smtp_password, to)


def _send(subject: str, body: str, smtp_user: str, smtp_password: str, to: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    raw = msg.as_string()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to, raw)
    logger.info("Email sent: %s", subject)
