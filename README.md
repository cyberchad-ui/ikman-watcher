# ikman-watcher

Polls ikman.lk every 15 minutes for new house and apartment rentals in Colombo (Rs 50,000–75,000, 1–2 bedrooms) and sends new finds by email.

## Setup

### 1. Gmail App Password

1. Go to your Google Account → Security → 2-Step Verification (must be enabled).
2. Search for "App passwords" at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Select app: **Mail**, device: **Other**, name: `ikman-watcher`. Click **Generate**.
4. Copy the 16-character password — you will not see it again.

### 2. GitHub Repo Secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|-------|
| `GMAIL_USER` | Your Gmail address (e.g. `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | 16-char app password from step 1 |
| `GMAIL_TO` | Recipient email address |

### 3. Enable GitHub Actions

Actions are enabled by default on public repos. The workflow runs every 15 minutes and commits updated state back to the repo. Trigger a manual run via **Actions → ikman-watcher → Run workflow** to verify setup.

## Config

Edit `config.yaml` to adjust price range, bedroom count, or toggle notifications:

```yaml
filters:
  price_min: 50000
  price_max: 75000
  beds_min: 1
  beds_max: 2

gmail:
  enabled: true
```

## State

`state/seen.json` tracks which ad IDs have been notified. IDs older than 60 days are pruned automatically. On the very first run all current ads are recorded as seen (no email flood).

## Scraping Notes

The watcher first looks for embedded JSON (`__NEXT_DATA__` or `window.initialData`) in the page. If ikman.lk changes its page structure and 0 ads are returned, a warning email is sent (at most once per 24 hours). Check GitHub Actions logs if alerts stop.

## WhatsApp

WhatsApp / CallMeBot support is stubbed in `config.yaml` (`whatsapp.enabled: false`) and will be added in a future iteration.
