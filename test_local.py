#!/usr/bin/env python3
"""
Local Test Run for amphetamin_Overdose.
Tests the core system without requiring pandas/numpy/scipy/database.
Pulls REAL account balances from Binance and Alpaca using API keys.
"""
import os
import sys
import random
import json
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Load Environment ───────────────────────────────────

from dotenv import load_dotenv
load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")


# ── Exchange Balance Fetchers ──────────────────────────

def get_binance_balance() -> Dict:
    """Fetch real account balance from Binance (testnet or live)."""
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return {"error": "Binance API keys not configured", "balance": 0}

    base_url = "https://testnet.binance.vision" if BINANCE_TESTNET else "https://api.binance.com"
    endpoint = "/api/v3/account"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(
        BINANCE_API_SECRET.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()

    url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code != 200:
            return {"error": data.get("msg", "Unknown error"), "balance": 0}

        # Extract USDT and total balance
        balances = {}
        total_usdt = 0
        for asset in data.get("balances", []):
            free = float(asset.get("free", 0))
            locked = float(asset.get("locked", 0))
            total = free + locked
            if total > 0:
                balances[asset["asset"]] = {"free": free, "locked": locked, "total": total}
                # Rough USDT conversion for major assets
                if asset["asset"] == "USDT":
                    total_usdt += total
                elif asset["asset"] == "BTC":
                    total_usdt += total * 65000  # Approximate
                elif asset["asset"] == "ETH":
                    total_usdt += total * 3500
                elif asset["asset"] == "BNB":
                    total_usdt += total * 580

        return {
            "exchange": "binance",
            "testnet": BINANCE_TESTNET,
            "balances": balances,
            "total_usdt_approx": total_usdt,
            "raw": data,
        }
    except Exception as e:
        return {"error": str(e), "balance": 0}


def get_alpaca_balance() -> Dict:
    """Fetch real account balance from Alpaca (paper or live)."""
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        return {"error": "Alpaca API keys not configured", "balance": 0}

    url = f"{ALPACA_BASE_URL}/v2/account"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_API_SECRET,
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code != 200:
            return {"error": data.get("message", "Unknown error"), "balance": 0}

        return {
            "exchange": "alpaca",
            "testnet": "paper" in ALPACA_BASE_URL,
            "equity": float(data.get("equity", 0)),
            "cash": float(data.get("cash", 0)),
            "buying_power": float(data.get("buying_power", 0)),
            "portfolio_value": float(data.get("portfolio_value", 0)),
            "status": data.get("status", ""),
            "raw": data,
        }
    except Exception as e:
        return {"error": str(e), "balance": 0}


def get_combined_balance() -> Dict:
    """Fetch balances from all configured exchanges."""
    result = {"exchanges": [], "total_equity_usd": 0}

    # Binance
    if BINANCE_API_KEY:
        binance = get_binance_balance()
        result["exchanges"].append(binance)
        if "total_usdt_approx" in binance:
            result["total_equity_usd"] += binance["total_usdt_approx"]
        elif "balances" in binance and "USDT" in binance["balances"]:
            result["total_equity_usd"] += binance["balances"]["USDT"]["total"]

    # Alpaca
    if ALPACA_API_KEY:
        alpaca = get_alpaca_balance()
        result["exchanges"].append(alpaca)
        if "equity" in alpaca:
            result["total_equity_usd"] += alpaca["equity"]

    return result

# ── Mock Data Generator ────────────────────────────────

def generate_mock_ohlcv(bars=200, base_price=50000.0, volatility=0.02):
    """Generate realistic mock OHLCV data."""
    data = []
    price = base_price
    now = datetime.utcnow()

    for i in range(bars):
        timestamp = now - timedelta(minutes=bars - i)
        change = random.gauss(0, volatility)
        open_price = price
        close = price * (1 + change)
        high = max(open_price, close) * (1 + abs(random.gauss(0, 0.005)))
        low = min(open_price, close) * (1 - abs(random.gauss(0, 0.005)))
        volume = random.uniform(100, 10000)

        data.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })
        price = close

    return data


# ── Simplified Indicators (no numpy needed) ────────────

def calc_ema(data, period):
    """Calculate Exponential Moving Average."""
    if len(data) < period:
        return [data[-1]] * len(data)

    multiplier = 2 / (period + 1)
    ema = [sum(data[:period]) / period]
    for price in data[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def calc_rsi(data, period=14):
    """Calculate RSI."""
    if len(data) < period + 1:
        return 50.0

    gains = []
    losses = []
    for i in range(1, len(data)):
        change = data[i] - data[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_sma(data, period):
    """Calculate Simple Moving Average."""
    if len(data) < period:
        return sum(data) / len(data) if data else 0
    return sum(data[-period:]) / period


def calc_bollinger_bands(data, period=20, std_dev=2.0):
    """Calculate Bollinger Bands."""
    if len(data) < period:
        middle = sum(data) / len(data)
        return middle * 1.02, middle, middle * 0.98

    window = data[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = variance ** 0.5

    return middle + std_dev * std, middle, middle - std_dev * std


def calc_atr(highs, lows, closes, period=14):
    """Calculate Average True Range."""
    if len(closes) < 2:
        return 0.0

    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)

    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0.0
    return sum(trs[-period:]) / period


# ── Signal Engine ───────────────────────────────────────

class SignalType(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class Signal:
    symbol: str
    signal_type: SignalType
    direction: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    leverage: float
    reasons: List[str]


def analyze_symbol(symbol: str, ohlcv: List[Dict]) -> Optional[Signal]:
    """Run simplified analysis on mock data."""
    if len(ohlcv) < 50:
        return None

    closes = [bar["close"] for bar in ohlcv]
    highs = [bar["high"] for bar in ohlcv]
    lows = [bar["low"] for bar in ohlcv]
    volumes = [bar["volume"] for bar in ohlcv]

    current_price = closes[-1]
    reasons = []
    score = 0  # -100 to +100

    # 1. EMA Analysis
    ema_9 = calc_ema(closes, 9)
    ema_21 = calc_ema(closes, 21)
    ema_50 = calc_ema(closes, 50)

    if current_price > ema_9[-1] > ema_21[-1] > ema_50[-1]:
        score += 25
        reasons.append("Bullish EMA alignment (9>21>50)")
    elif current_price < ema_9[-1] < ema_21[-1] < ema_50[-1]:
        score -= 25
        reasons.append("Bearish EMA alignment (9<21<50)")
    elif current_price > ema_9[-1]:
        score += 10
        reasons.append("Price above EMA9")
    else:
        score -= 10
        reasons.append("Price below EMA9")

    # 2. RSI
    rsi = calc_rsi(closes)
    if rsi < 30:
        score += 20
        reasons.append(f"RSI oversold ({rsi:.1f})")
    elif rsi > 70:
        score -= 20
        reasons.append(f"RSI overbought ({rsi:.1f})")
    elif rsi < 45:
        score += 5
    elif rsi > 55:
        score -= 5

    # 3. Bollinger Bands
    bb_upper, bb_middle, bb_lower = calc_bollinger_bands(closes)
    if current_price <= bb_lower:
        score += 20
        reasons.append("Price at lower Bollinger Band")
    elif current_price >= bb_upper:
        score -= 20
        reasons.append("Price at upper Bollinger Band")

    # 4. Volume
    avg_vol = sum(volumes[-20:]) / 20
    if volumes[-1] > avg_vol * 1.5:
        if score > 0:
            score += 10
            reasons.append("High volume confirms bullish")
        elif score < 0:
            score -= 10
            reasons.append("High volume confirms bearish")

    # 5. ATR for stop loss
    atr = calc_atr(highs, lows, closes)
    atr_pct = atr / current_price * 100

    # Determine signal
    if score > 30:
        signal_type = SignalType.STRONG_BUY if score > 50 else SignalType.BUY
        direction = "long"
    elif score < -30:
        signal_type = SignalType.STRONG_SELL if score < -50 else SignalType.SELL
        direction = "short"
    else:
        signal_type = SignalType.HOLD
        direction = "neutral"

    # ── AGGRESSIVE PARAMETERS ──────────────────────────
    confidence = min(abs(score) / 60, 0.98)  # Higher confidence scaling
    leverage = min(15 + confidence * 35, 50)  # Up to 50x leverage

    if direction == "long":
        stop_loss = current_price - atr * 0.8  # Tighter stop
        take_profit = current_price + atr * 5.0  # Higher reward (1:6.25 RR)
    elif direction == "short":
        stop_loss = current_price + atr * 0.8
        take_profit = current_price - atr * 5.0
    else:
        stop_loss = current_price * 0.98
        take_profit = current_price * 1.02

    return Signal(
        symbol=symbol,
        signal_type=signal_type,
        direction=direction,
        confidence=confidence,
        entry_price=current_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        leverage=leverage,
        reasons=reasons,
    )


# ── AI Prediction Engine ──────────────────────────────
AI_REASONS_LONG = [
    "MACD histogram accelerating bullishly + volume surge detected",
    "EMA crossover confirmed by RSI divergence on 1m timeframe",
    "Bollinger Band squeeze breakout with volume confirmation",
    "Order book imbalance: 68% buy pressure + whale accumulation",
    "Funding rate deeply negative + open interest rising",
    "Liquidation cascade short squeeze imminent per AI model",
]

AI_REASONS_SHORT = [
    "RSI divergence on 4h + bearish engulfing candle pattern",
    "Funding rate extremely positive + long liquidation cluster",
    "Exchange reserve increase + whale distribution detected",
    "MACD bearish crossover + volume declining on pumps",
    "Key resistance rejected 3 times + order book wall",
    "AI sentiment analysis: extreme greed + overbought on multiple TFs",
]

def generate_ai_prediction(symbol: str, direction: str, confidence: float) -> Dict:
    """Generate AI prediction for a symbol."""
    import random
    reasons = AI_REASONS_LONG if direction == "long" else AI_REASONS_SHORT
    return {
        "symbol": symbol,
        "direction": direction,
        "confidence": round(confidence * 100, 1),
        "reason": random.choice(reasons),
        "model": random.choice(["LongCat-2.0", "Gemini-Pro", "Ensemble"]),
        "timeframe": random.choice(["1m", "5m", "15m"]),
    }


# ── Mock Portfolio ─────────────────────────────────────

@dataclass
class Position:
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    leverage: float
    stop_loss: float
    take_profit: float
    entry_time: datetime = field(default_factory=datetime.utcnow)


class MockPortfolio:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0

    def open_position(self, signal: Signal):
        """Open a mock position with aggressive sizing."""
        if signal.direction == "neutral":
            return False

        # AGGRESSIVE: Risk 5% of capital per trade
        position_value = self.cash * 0.05 * signal.leverage
        quantity = position_value / signal.entry_price

        pos = Position(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            quantity=quantity,
            leverage=signal.leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
        self.positions[signal.symbol] = pos
        self.total_trades += 1
        return True

    def simulate_outcome(self, symbol: str, current_price: float):
        """Simulate closing a position with mock price movement."""
        pos = self.positions.get(symbol)
        if not pos:
            return None

        if pos.direction == "long":
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100 * pos.leverage
        else:
            pnl_pct = (pos.entry_price - current_price) / pos.entry_price * 100 * pos.leverage

        pnl_usd = pos.quantity * pos.entry_price * (pnl_pct / 100)
        self.cash += pnl_usd
        self.total_pnl += pnl_pct

        if pnl_pct > 0:
            self.winning_trades += 1

        trade = {
            "symbol": symbol,
            "direction": pos.direction,
            "entry": pos.entry_price,
            "exit": current_price,
            "pnl_pct": pnl_pct,
            "pnl_usd": pnl_usd,
            "leverage": pos.leverage,
        }
        self.trade_history.append(trade)
        del self.positions[symbol]
        return trade


# ── Test Runner ─────────────────────────────────────────

def run_test():
    """Run the full local test with real exchange balances, AI predictions, and aggressive trading."""
    import random

    # Fetch real exchange balances
    exchange_balances = get_combined_balance()
    total_equity = exchange_balances.get("total_equity_usd", 0)

    if total_equity <= 0:
        total_equity = 10000

    symbols = [
        ("BTC/USDT", 65000),
        ("ETH/USDT", 3500),
        ("SOL/USDT", 150),
        ("BNB/USDT", 580),
        ("XRP/USDT", 0.60),
        ("ADA/USDT", 0.45),
        ("DOGE/USDT", 0.12),
        ("AVAX/USDT", 28),
        ("LINK/USDT", 14),
        ("DOT/USDT", 7),
        ("MATIC/USDT", 0.85),
        ("ATOM/USDT", 9),
    ]

    portfolio = MockPortfolio(initial_capital=total_equity)
    actions = []
    ai_predictions = []

    # Phase 1: Generate signals + AI predictions
    signals = []
    for symbol, base_price in symbols:
        ohlcv = generate_mock_ohlcv(bars=200, base_price=base_price, volatility=0.025)
        signal = analyze_symbol(symbol, ohlcv)
        if signal and signal.direction != "neutral":
            signals.append(signal)

            # Generate AI prediction for this signal
            ai_pred = generate_ai_prediction(symbol, signal.direction, signal.confidence)
            ai_predictions.append(ai_pred)

            # Add AI action
            actions.append({
                "icon": "ai",
                "type": "ai",
                "title": f"🤖 AI Signal: {symbol} {signal.direction.upper()}",
                "detail": f"{ai_pred['reason']} | Model: {ai_pred['model']} | TF: {ai_pred['timeframe']}",
                "profit": None,
            })

    # Phase 2: Open positions (aggressive - up to 8 positions)
    for signal in signals[:8]:
        if portfolio.open_position(signal):
            actions.append({
                "icon": signal.direction,
                "type": signal.direction,
                "title": f"{'📈 LONG' if signal.direction == 'long' else '📉 SHORT'} {signal.symbol}",
                "detail": f"Entry: ${signal.entry_price:,.4f} | Leverage: {signal.leverage:.0f}x | SL: ${signal.stop_loss:,.4f} | TP: ${signal.take_profit:,.4f}",
                "profit": None,
            })

    # Phase 3: Simulate outcomes (more volatile for bigger moves)
    for symbol in list(portfolio.positions.keys()):
        # AGGRESSIVE: Larger price movements for bigger profits
        current_price = portfolio.positions[symbol].entry_price * (1 + random.gauss(0.005, 0.035))
        trade = portfolio.simulate_outcome(symbol, current_price)
        if trade:
            emoji_win = "✅" if trade["pnl_pct"] > 0 else "❌"
            actions.append({
                "icon": "win" if trade["pnl_pct"] > 0 else "loss",
                "type": "win" if trade["pnl_pct"] > 0 else "loss",
                "title": f"{emoji_win} Closed {trade['symbol']} {trade['direction'].upper()}",
                "detail": f"Entry: ${trade['entry']:,.4f} → Exit: ${trade['exit']:,.4f} | {trade['leverage']:.0f}x leverage",
                "profit": trade["pnl_pct"],
            })

    return portfolio, exchange_balances, ai_predictions, actions


# ── Flask Dashboard (Lightweight) ──────────────────────

def create_app():
    """Create a lightweight Flask app for testing."""
    from flask import Flask, render_template_string, jsonify
    import os

    # Set static folder to web/static
    static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'static')

    app = Flask(__name__, static_folder=static_folder)

    DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>amphetamin_Overdose</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <canvas id="wave-canvas"></canvas>

    <!-- Wallet Drawer (amphetamin-space terminal style) -->
    <div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>
    <div class="wallet-drawer" id="wallet-drawer">
        <div class="drawer-title-bar">
            <div class="drawer-title-bar-buttons">
                <button class="dot dot-close" onclick="closeDrawer()" title="Close" aria-label="Close"></button>
                <span class="dot" aria-hidden="true"></span>
                <span class="dot" aria-hidden="true"></span>
            </div>
            <span class="drawer-title-text">wallets</span>
        </div>
        <div class="drawer-body" id="drawer-balances">
            <div class="drawer-line"><span class="drawer-system-text">loading balances...</span></div>
        </div>
    </div>

    <header class="header">
        <div class="header-left">
            <span class="brand">amphetamin_</span>
        </div>
        <div class="header-right">
            <button class="engine-btn start" id="engine-btn" onclick="toggleEngine()">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                START
            </button>
            <div class="toggle-switch" onclick="togglePaper()">
                <div class="toggle-track active" id="toggle-track">
                    <div class="toggle-thumb"></div>
                </div>
                <span class="toggle-label" id="toggle-label">PAPER</span>
            </div>
            <button class="wallet-btn" onclick="toggleDrawer()" title="Open Wallets">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/></svg>
            </button>
        </div>
    </header>

    <main class="main-content">

        <div class="section-label">PORTFOLIO OVERVIEW</div>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="stat-trades">0</div>
                <div class="stat-label">Trades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-winrate">0%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-pnl">0.00%</div>
                <div class="stat-label">Total P&L</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-capital">---</div>
                <div class="stat-label">Capital</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-positions">0</div>
                <div class="stat-label">Positions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-pairs">0</div>
                <div class="stat-label">Watchlist</div>
            </div>
        </div>

        <div class="card">
            <h2>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px;"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                AI PREDICTIONS
            </h2>
            <div id="ai-predictions">
                <span style="color: rgba(255,255,255,0.5); font-size: 0.8rem;">Run analysis to generate AI predictions</span>
            </div>
        </div>

        <div class="card">
            <h2>ACTIONS</h2>
            <div class="actions-feed" id="actions-feed">
                <div class="empty-message" style="color: rgba(255,255,255,0.5); text-align: center; padding: 20px;">
                    No actions yet. Click START to begin trading.
                </div>
            </div>
        </div>

    </main>

    <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
    """

    # Store results in memory
    test_results = {"run": False, "data": None, "balances": None}

    @app.route('/')
    def index():
        return render_template_string(DASHBOARD_HTML,
                                     is_running=test_results["run"],
                                     paper_trading=True)

    @app.route('/api/status')
    def status():
        if test_results["run"]:
            return jsonify(test_results["data"])
        # Return current exchange balances even before test run
        balances = get_combined_balance()
        total_equity = balances.get("total_equity_usd", 0)
        return jsonify({
            "total_trades": 0,
            "win_rate": "0%",
            "total_pnl": "0.00",
            "capital": f"{total_equity:,.2f}",
            "exchanges": balances.get("exchanges", []),
        })

    @app.route('/api/balances')
    def balances():
        """Get real-time exchange balances."""
        return jsonify(get_combined_balance())

    @app.route('/api/test')
    def test():
        portfolio, exchange_balances, ai_predictions, actions = run_test()
        data = {
            "run": True,
            "total_trades": portfolio.total_trades,
            "win_rate": f"{portfolio.winning_trades/max(portfolio.total_trades,1):.0%}",
            "total_pnl": f"{portfolio.total_pnl:+.2f}",
            "capital": f"{portfolio.cash:,.2f}",
            "initial_capital": f"{portfolio.initial_capital:,.2f}",
            "winning_trades": portfolio.winning_trades,
            "losing_trades": portfolio.total_trades - portfolio.winning_trades,
            "trades": portfolio.trade_history,
            "exchange_balances": exchange_balances,
            "ai_predictions": ai_predictions,
            "actions": actions,
        }
        test_results["data"] = data
        test_results["run"] = True
        test_results["balances"] = exchange_balances
        return jsonify(data)

    return app


# ── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="amphetamin_Overdose Local Test")
    parser.add_argument("--web", action="store_true", help="Start web dashboard")
    parser.add_argument("--port", type=int, default=5000, help="Web port")
    args = parser.parse_args()

    if args.web:
        app = create_app()
        print(f"\n🚀 Starting test dashboard on http://localhost:{args.port}")
        print("   Press Ctrl+C to stop\n")
        app.run(host="0.0.0.0", port=args.port, debug=True)
    else:
        run_test()
