import logging
import os

import requests

log = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 10

_session = requests.Session()

def send_message(
    text: str,
    *,
    token: str | None = None,
    chat_id: str | None = None,
    parse_mode: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    api_base: str = API_BASE,
) -> bool:
    """Invia un messaggio al bot Telegram. Restituisce True se inviato."""
    token = token or os.getenv("TELEGRAM_BOT")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT / TELEGRAM_CHAT_ID non configurati.")

    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        r = _session.post(
            f"{api_base}/bot{token}/sendMessage",
            json=payload,
            timeout=timeout,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        # niente str(e): contiene l'URL con il token
        log.error("Invio Telegram fallito: %s", type(e).__name__)
        return False

    log.info("Notifica inviata al bot Telegram")
    return True