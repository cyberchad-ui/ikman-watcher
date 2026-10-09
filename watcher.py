import logging
import os

import yaml

import notifier
import scraper
import state
from filters import apply_filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run(config_path: str = "config.yaml") -> None:
    cfg = _load_config(config_path)
    filters = cfg["filters"]
    s = state.load()

    all_ads: list[scraper.Ad] = []
    for url in cfg["sources"]:
        try:
            html = scraper.fetch(url)
            ads = scraper.parse(html)
            logger.info("Fetched %d ads from %s", len(ads), url)
            all_ads.extend(ads)
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", url, exc)

    if not all_ads:
        logger.warning("0 ads returned from all sources")
        if not state.is_first_run(s) and state.should_send_zero_alert(s):
            try:
                _send_error("0 ads returned from all sources. The site structure may have changed.", cfg)
            except Exception as exc:
                logger.error("Failed to send zero-ads alert: %s", exc)
            state.mark_zero_alert_sent(s)
        state.save(s)
        return

    filtered = apply_filters(
        all_ads,
        price_min=filters["price_min"],
        price_max=filters["price_max"],
        beds_min=filters["beds_min"],
        beds_max=filters["beds_max"],
        areas=filters.get("areas") or None,
    )

    if state.is_first_run(s):
        logger.info("First run — marking %d ads as seen without alerting", len(filtered))
        for ad in filtered:
            state.mark_seen(s, ad.slug)
        s["first_run_done"] = True
        state.prune(s)
        state.save(s)
        return

    new_ads = [ad for ad in filtered if not state.is_seen(s, ad.slug)]
    logger.info("%d new ads after filtering", len(new_ads))

    if new_ads:
        if cfg.get("telegram", {}).get("enabled"):
            _send_telegram_new_ads(new_ads, cfg)
        if cfg.get("gmail", {}).get("enabled"):
            _send_gmail_new_ads(new_ads, cfg)

    for ad in new_ads:
        state.mark_seen(s, ad.slug)

    state.prune(s)
    state.save(s)


def _load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _telegram_creds() -> tuple[str, str]:
    return os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHANNEL_ID"]


def _smtp_creds() -> tuple[str, str, str]:
    return os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"], os.environ["GMAIL_TO"]


def _send_telegram_new_ads(ads: list[scraper.Ad], cfg: dict) -> None:
    token, channel_id = _telegram_creds()
    notifier.send_telegram_new_ads(ads, bot_token=token, channel_id=channel_id)


def _send_gmail_new_ads(ads: list[scraper.Ad], cfg: dict) -> None:
    user, password, to = _smtp_creds()
    notifier.send_new_ads(ads, smtp_user=user, smtp_password=password, to=to)


def _send_error(message: str, cfg: dict) -> None:
    if cfg.get("telegram", {}).get("enabled"):
        token, channel_id = _telegram_creds()
        notifier.send_telegram_error(message, bot_token=token, channel_id=channel_id)
    elif cfg.get("gmail", {}).get("enabled"):
        user, password, to = _smtp_creds()
        notifier.send_error(message, smtp_user=user, smtp_password=password, to=to)


if __name__ == "__main__":
    run()
