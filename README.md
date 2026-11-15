# 🔔 Stock Price Alert

Script che controlla i prezzi di azioni ed ETF (dati Yahoo Finance) e invia una **notifica su Telegram** quando un titolo supera una soglia superiore o scende sotto una soglia inferiore.

Gli alert **non sono nel codice**: sono salvati su **Firebase (Firestore)**, nella collection `alerts`. Per aggiungere, modificare o disattivare un alert basta intervenire sul database, senza toccare lo script.

---

## ⚙️ Configurazione

### 1. Crea il bot Telegram
1. Su Telegram apri **@BotFather** e invia `/newbot`
2. Scegli nome e username del bot e copia il **token** che ti viene consegnato
3. Scrivi un messaggio qualsiasi al tuo nuovo bot
4. Apri nel browser `https://api.telegram.org/bot<TOKEN>/getUpdates` e cerca il campo `chat` → `id`: è il tuo **chat id**

> Il token dà il controllo del bot: non condividerlo e non committarlo nel repository. Se finisce in un log o in un repo pubblico, rigeneralo da @BotFather con `/revoke`.

### 2. Crea la chiave del service account Firebase
1. Nella [console Firebase](https://console.firebase.google.com) apri il progetto → **Impostazioni progetto** → **Account di servizio**
2. Clicca **Genera nuova chiave privata** e scarica il file JSON
3. **Non committarlo mai nel repository** (aggiungilo al `.gitignore`): chi lo possiede ha accesso al database

### 3. Aggiungi i Secret su GitHub
Nel tuo repository GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Crea questi tre secret:

| Nome | Valore |
|---|---|
| `TELEGRAM_BOT` | il token del bot (punto 1) |
| `TELEGRAM_CHAT_ID` | il chat id (punto 1) |
| `FIREBASE_CREDENTIALS_JSON` | l'**intero contenuto** del file JSON del punto 2 |

### 4. Crea gli alert su Firestore
Collection `alerts`, **un documento per alert**:

| Campo | Tipo | Descrizione |
|---|---|---|
| `ticker` | string | Ticker Yahoo Finance, es. `ENI.MI` |
| `name` | string, opzionale | Nome mostrato nel messaggio. Se manca si usa il ticker |
| `above` | number, opzionale | Soglia superiore: notifica quando il prezzo è **≥** a questo valore |
| `below` | number, opzionale | Soglia inferiore: notifica quando il prezzo è **≤** a questo valore |
| `currency` | string, opzionale | Etichetta della valuta nel messaggio. Se manca vale `EUR` |
| `active` | boolean, opzionale | `false` = alert saltato. Se manca vale `true` |

Esempio:
```
ticker:   "UCG.MI"
name:     "Unicredit"
above:    95
below:    60.5
currency: "EUR"
active:   true
```

Note:
- Puoi usare solo `above`, solo `below` o entrambe.
- Le soglie vanno espresse **nella valuta in cui il ticker è quotato su Yahoo**. Il campo `currency` è solo un'etichetta per il messaggio: **non** converte nulla.
- Imposta `active` come **boolean** dalla console Firebase, non come testo.
- Verifica sempre i ticker su Yahoo (suffisso di borsa e quotazione giusta).

### 5. Gestione automatica dei campi di stato
Lo script crea e aggiorna da solo due campi in ogni alert, non devi scriverli tu:

| Campo | Significato |
|---|---|
| `above_notified` | `true` se la notifica per la soglia superiore è già stata inviata |
| `below_notified` | `true` se la notifica per la soglia inferiore è già stata inviata |

---

## 🔁 Come funziona

A ogni esecuzione lo script:
1. legge dalla collection `alerts` gli alert attivi;
2. scarica l'ultimo prezzo di ciascun ticker (una sola richiesta per ticker, anche se ha più alert);
3. confronta il prezzo con le soglie e invia i messaggi su Telegram.

**Niente notifiche ripetute.** Una soglia notifica **una sola volta**, nel momento in cui viene superata. Se il prezzo resta oltre la soglia, le esecuzioni successive non inviano altro. L'alert si **riarma** da solo quando il prezzo rientra dalla parte giusta della soglia.

- Il flag viene aggiornato solo se il messaggio Telegram parte davvero: se l'invio fallisce, l'esecuzione successiva riprova.
- Se modifichi una soglia mentre il prezzo è ancora oltre il nuovo valore e il flag è `true`, non arriverà una nuova notifica. Per forzarla, imposta a mano il flag (`above_notified` o `below_notified`) a `false`.

Lo script fa **un solo controllo per esecuzione** e poi termina: quanto spesso controllare lo decide l'utente (vedi sotto).

---

## ⏰ Avvio automatico

L'avvio periodico è affidato a un **cronjob esterno** e non allo `schedule` di GitHub Actions, perché l'esecuzione dei job schedulati di GitHub non è affidabile (possono partire in ritardo o non partire affatto).

Il cronjob avvia il workflow chiamando l'API di GitHub, grazie al trigger `workflow_dispatch`:

```
POST /repos/<utente>/<repo>/actions/workflows/<file>.yml/dispatches
```

con un token che abbia il permesso *Actions: write*.

**La frequenza dei controlli è decisa dall'utente**, impostandola nel servizio di cron scelto.

---

## 🧪 Test manuale
Puoi avviarlo subito, senza aspettare il prossimo controllo programmato:
1. Vai nel tuo repository → **Actions**
2. Seleziona il workflow dell'alert
3. Clicca **Run workflow** → **Run workflow**

In locale, con un file `.env` contenente le variabili d'ambiente:

```env
TELEGRAM_BOT=...
TELEGRAM_CHAT_ID=...
FIREBASE_CREDENTIALS=percorso/al/serviceAccount.json
```

```bash
python stock_alert.py
```

---

## 📦 Dipendenze
- `yfinance` — prezzi di borsa
- `requests` — invio dei messaggi a Telegram
- `firebase-admin` — lettura degli alert da Firestore
- `python-dotenv` — caricamento del file `.env` in locale

```bash
pip install yfinance requests python-dotenv firebase-admin
```

---

## ⚠️ Note
- I prezzi provengono da Yahoo Finance e possono avere ritardi o piccoli errori. Per alcune borse il dato è differito.
- Il log su file (`stock_alert.log`) non persiste sul runner di GitHub: per consultare i log di un'esecuzione usa la tab **Actions**.
- Le notifiche sono puramente informative e non costituiscono consulenza finanziaria.
