# 🤖 Binance Futures Testnet Trading Bot

A clean, minimal Python CLI application for placing **MARKET**, **LIMIT**, and **STOP_MARKET** orders on the **Binance USDT-M Futures Testnet** via direct REST API calls.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Testnet](https://img.shields.io/badge/Binance-Futures%20Testnet-yellow)

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package surface
│   ├── client.py            # Binance REST client (signing, retries, errors)
│   ├── orders.py            # Order placement logic + OrderResult dataclass
│   ├── validators.py        # Pure input validation
│   └── logging_config.py   # Rotating file + console log setup
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log      # Auto-created at runtime
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## ⚙️ Prerequisites

- Python **3.9+**
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account with API credentials

---

## 🚀 Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/binance-futures-trading-bot.git
cd binance-futures-trading-bot
```

### 2. Create a virtual environment (recommended)

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get your Testnet API credentials

1. Visit [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Generate an API Key + Secret from the dashboard
4. Copy both values — the **Secret is shown only once**

### 5. Set your credentials as environment variables

**macOS / Linux:**
```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Windows PowerShell:**
```powershell
$env:BINANCE_API_KEY="your_api_key_here"
$env:BINANCE_API_SECRET="your_api_secret_here"
```

> ⚠️ Never hardcode credentials in source code or commit them to Git.

---

## 📦 How to Run

### Market Order — BUY
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Market Order — SELL
```bash
python cli.py --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01
```

### Limit Order — BUY
```bash
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 95000
```

### Limit Order — SELL
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 120000
```

### Stop-Market Order — BUY (bonus order type)
```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 108000
```

### Custom Time-In-Force (LIMIT orders)
```bash
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 4000 --tif IOC
```

### Debug logging
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG
```

---

## 🖥️ Sample Output

```
──────────────────────────────────────────────────────
  ORDER REQUEST
──────────────────────────────────────────────────────
  Symbol:             BTCUSDT
  Side:               BUY
  Type:               MARKET
  Quantity:           0.01

──────────────────────────────────────────────────────
  ORDER RESPONSE
──────────────────────────────────────────────────────
  Order ID:           4051765192
  Client ID:          web_AXuEAqFXVobfnBGfK3nH
  Symbol:             BTCUSDT
  Side:               BUY
  Type:               MARKET
  Status:             FILLED
  Original Qty:       0.01
  Executed Qty:       0.01
  Avg Fill Price:     107432.50000

  ✓  Order placed successfully!
  Log file: logs/trading_bot.log
```

---

## 🛠️ CLI Reference

| Flag           | Required | Description                                              |
|----------------|----------|----------------------------------------------------------|
| `--symbol`     | ✅       | Trading pair e.g. `BTCUSDT`, `ETHUSDT`                  |
| `--side`       | ✅       | `BUY` or `SELL`                                          |
| `--type`       | ✅       | `MARKET`, `LIMIT`, or `STOP_MARKET`                      |
| `--quantity`   | ✅       | Order quantity — must be ≥ $100 notional value           |
| `--price`      | ⚠️       | Required for `LIMIT` orders                              |
| `--stop-price` | ⚠️       | Required for `STOP_MARKET` orders                        |
| `--tif`        | ❌       | Time-in-force: `GTC` *(default)*, `IOC`, `FOK`          |
| `--api-key`    | ❌*      | API key *(or set `BINANCE_API_KEY` env var)*             |
| `--api-secret` | ❌*      | API secret *(or set `BINANCE_API_SECRET` env var)*       |
| `--log-level`  | ❌       | `DEBUG` / `INFO` *(default)* / `WARNING` / `ERROR`      |
| `--no-colour`  | ❌       | Disable ANSI colour in terminal output                   |

---

## 📋 Logging

All activity is written to `logs/trading_bot.log`:

- ✅ Every outbound API request (method, endpoint, params — signature redacted)
- ✅ Every inbound response (HTTP status, response body)
- ✅ Validation errors (before any network call)
- ✅ Binance API errors (error code + message)
- ✅ Network failures (timeouts, connection errors)

Logs rotate at **5 MB** with **3 backups** retained.

---

## 🔒 Error Handling

| Error Class           | Cause                                                  |
|-----------------------|--------------------------------------------------------|
| `ValidationError`     | Invalid symbol, bad quantity/price, missing fields     |
| `BinanceAPIError`     | Binance returned `{"code": <negative>, "msg": "..."}`  |
| `BinanceNetworkError` | Timeout, DNS failure, connection refused               |

**Common errors and fixes:**

| Code    | Message                              | Fix                                      |
|---------|--------------------------------------|------------------------------------------|
| `-1021` | Timestamp outside recvWindow         | Sync your system clock                   |
| `-1121` | Invalid symbol                       | Check symbol name (e.g. `BTCUSDT`)       |
| `-4164` | Notional must be ≥ 100               | Increase quantity (use `0.01` for BTC)   |
| `-2010` | Insufficient balance                 | Check testnet wallet balance             |

---

## 📝 Assumptions

1. **Testnet only** — base URL is hard-coded to `https://testnet.binancefuture.com`
2. **One-way mode** — `positionSide` defaults to `BOTH` (hedge mode not supported)
3. **Quantity precision** is the caller's responsibility — use values matching the exchange's lot-size filter
4. **No leverage management** — set leverage separately via the Testnet UI
5. Only `requests` is used as a runtime dependency — no Binance SDK

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
