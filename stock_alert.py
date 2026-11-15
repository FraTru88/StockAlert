"""
Stock Price Alert App
Legge gli alert da Firestore, controlla i prezzi con yfinance
e invia notifiche a un bot Telegram.

Dipendenze:
    pip install yfinance requests python-dotenv firebase-admin

Variabili d'ambiente (.env):
    TELEGRAM_BOT=...
    TELEGRAM_CHAT_ID=...
    FIREBASE_CREDENTIALS=serviceAccount.json   (in locale)
    FIREBASE_CREDENTIALS_JSON={...contenuto del JSON...}   (GitHub Actions)

Struttura Firestore di esempio (collection "alerts", un documento per alert):
    ticker:   "UCG.MI"        (string)
    name:     "Unicredit"     (string, opzionale)
    above:    95.0            (number, opzionale)
    below:    60.0            (number, opzionale)
    currency: "EUR"           (string, opzionale)
    active:   true            (bool, opzionale, default true)
    # campi gestiti dallo script per evitare notifiche ripetute:
    above_notified: false
    below_notified: false
"""

import logging
import os

import requests
import yfinance as yf
from dotenv import load_dotenv
from firestore_client import init_firestore, get_collection, close_firestore
from telegram_client import send_message

load_dotenv()

TELEGRAM_BOT = os.getenv("TELEGRAM_BOT")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")

ALERTS_COLLECTION = "alerts"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("stock_alert.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
# requests/urllib3 a livello DEBUG loggano l'URL completo (con il token del bot)
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

session = requests.Session()

def load_alerts(db) -> list[tuple[object, dict]]:
    """Restituisce (riferimento documento, dati) per gli alert attivi."""
    alerts = []    
    for ref, data in get_collection(db, ALERTS_COLLECTION):
        if data.get("active", True) and data.get("ticker"):
            alerts.append((ref, data))
    return alerts

# ── Prezzo ────────────────────────────────────────────────────────────────────
def get_price(ticker: str) -> float | None:
    try:
        price = yf.Ticker(ticker).fast_info.last_price
        if price is None:
            log.warning("Prezzo non disponibile per %s", ticker)
            return None
        return round(float(price), 4)
    except Exception as e:
        log.error("Errore recupero prezzo %s: %s", ticker, e)
        return None

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message: str) -> bool:    
    return send_message(message)

# ── Logica alert ──────────────────────────────────────────────────────────────
def check_alerts(db):
    log.info("Controllo prezzi in corso...")
    prices: dict[str, float | None] = {}  # un solo fetch per ticker

    for ref, alert in load_alerts(db):
        ticker = alert["ticker"].upper()
        name = alert.get("name", ticker)
        above = alert.get("above")
        below = alert.get("below")
        currency = alert.get("currency", "EUR")

        if ticker not in prices:
            prices[ticker] = get_price(ticker)
        price = prices[ticker]
        if price is None:
            continue

        log.info("  %s (%s): %s %s", ticker, name, price, currency)
        updates = {}

        if above is not None:
            process_threshold(
                price >= above, alert, "above_notified",
                f"🚀 {name} ({ticker}) ha SUPERATO la soglia!\n"
                f"   Prezzo attuale: {price} {currency}\n"
                f"   Soglia superiore: {above} {currency}",
                updates,
            )

        if below is not None:
            process_threshold(
                price <= below, alert, "below_notified",
                f"🔻 {name} ({ticker}) è SCESO sotto la soglia!\n"
                f"   Prezzo attuale: {price} {currency}\n"
                f"   Soglia inferiore: {below} {currency}",
                updates,
            )

        if updates:
            ref.update(updates)

    log.info("Controllo completato.")

def process_threshold(hit: bool, alert: dict, flag: str, msg: str, updates: dict) -> None:
    """Invia la notifica al primo superamento e riarma l'alert quando rientra."""
    notified = alert.get(flag)
    if hit and not notified:
        if send_telegram(msg):
            updates[flag] = True
    elif not hit and notified:
        updates[flag] = False

def main():
    log.info("=== Stock Alert App avviata ===")
    if not TELEGRAM_BOT or not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT / TELEGRAM_CHAT_ID non configurati.")
    try:
        check_alerts(init_firestore())
    finally:
        close_firestore()

if __name__ == "__main__":
    main()