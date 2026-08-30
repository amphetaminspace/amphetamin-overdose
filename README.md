# amphetamin_Overdose

**Fully Automated AI-Powered Crypto Day Trading System**

> ⚠️ **DISCLAIMER**: This is an experimental trading system. Trading cryptocurrencies involves substantial risk of loss. Past performance does not guarantee future results. Always start with paper trading and never risk more than you can afford to lose. The 2x-10x daily return target is extremely aggressive and unlikely to be consistently achieved.

---

## Features

### Core Trading Engine
- **Multi-pair trading**: Monitors and trades up to 32 crypto pairs simultaneously
- **Day trading & scalping**: Optimized for 1m-15m timeframes
- **Margin/Leverage trading**: Supports up to 125x leverage (default cap: 25x)
- **Multi-exchange**: Binance (primary) + Alpaca (secondary)

### Technical Analysis (25+ Indicators)
| Category | Indicators |
|----------|-----------|
| **Trend** | EMA (9, 21, 50, 100, 200), Supertrend, Ichimoku, ADX, Hull MA |
| **Momentum** | RSI, MACD, Stochastic, CCI, Williams %R, TRIX |
| **Volatility** | Bollinger Bands, ATR, Keltner Channels, Donchian Channels |
| **Volume** | OBV, VWAP, MFI, Accumulation/Distribution Line |
| **Advanced** | Elder Ray, TTM Squeeze, Pivot Points |

### 6 Scalping Strategies
1. **EMA Crossover Scalping** - Fast EMA cross with trend alignment
2. **RSI + Stochastic** - Oversold/overbought with divergence
3. **Bollinger Band Breakout** - Squeeze detection with volume confirmation
4. **VWAP Mean Reversion** - Price reversion to VWAP in trends
5. **Volume-Weighted Momentum** - Volume-confirmed momentum entries
6. **MACD Histogram** - Momentum acceleration signals

### AI Integration
- **LongCat AI**: Market analysis, signal validation, strategy adaptation
- **Gemini AI**: Price prediction, sentiment analysis, trade planning
- **AI Ensemble**: Weighted consensus from both models

### Risk Management (8 Layers)
1. Daily loss limit (circuit breaker)
2. Max drawdown protection
3. Loss streak protection (auto-reduce size)
4. Win streak management
5. Portfolio exposure limits
6. Margin level protection
7. Dynamic leverage adjustment
8. Kelly Criterion position sizing

### Machine Learning
- **Adaptive Learning**: Learns from every trade outcome
- **Pattern Recognition**: Gradient Boosting classifier predicts win probability
- **Strategy Optimization**: Automatically adjusts strategy weights
- **Regime Detection**: Adapts to trending/ranging/volatile/calm markets

### Self-Optimization
- Parameter tuning every 30 minutes
- Stop loss / take profit ratio optimization
- Position size optimization (Kelly Criterion)
- Leverage adjustment based on performance
- Confidence threshold calibration

---

## Architecture

```
amphetamin_Overdose/
├── core/               # Main trading engine orchestrator
├── strategies/         # 6 scalping strategies + signal combiner
├── indicators/         # 25+ technical indicators
├── ai/                 # LongCat + Gemini integration
├── risk/               # 8-layer risk management
├── portfolio/          # Position & pair management
├── learning/           # ML model & adaptive learning
├── optimization/       # Self-optimization engine
├── exchanges/          # Binance + Alpaca clients
├── data/               # PostgreSQL + market data
├── backtesting/        # Historical backtesting
└── config/             # Settings & configuration
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (recommended)

### 1. Clone & Setup
```bash
cd amphetamin_Overdose
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start Infrastructure
```bash
docker-compose up -d postgres redis
```

### 4. Run
```bash
# Paper trading (recommended first)
python main.py --mode trade

# Scan for best pairs
python main.py --mode scan

# Run backtest
python main.py --mode backtest

# Check status
python main.py --mode status
```

### Docker (Full Stack)
```bash
docker-compose up -d
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PAIRS` | 32 | Max pairs to trade |
| `MAX_LEVERAGE` | 25 | Maximum leverage |
| `RISK_PER_TRADE` | 0.02 | Risk 2% per trade |
| `DAILY_LOSS_LIMIT` | 0.05 | Stop trading at 5% daily loss |
| `STOP_LOSS_PCT` | 0.015 | 1.5% base stop loss |
| `TAKE_PROFIT_PCT` | 0.045 | 4.5% base take profit |
| `PAPER_TRADING` | true | Paper trading mode |

---

## Trading Strategy Deep Dive

### Signal Generation Flow
1. **Market Scan**: Fetches top 50 pairs by volume, filters by spread/volatility
2. **Indicator Calculation**: Computes 25+ indicators on each pair
3. **Strategy Execution**: Runs 6 strategies in parallel
4. **Signal Combination**: Combines signals with weighted voting (min 2 agreeing)
5. **AI Validation**: LongCat + Gemini validate high-confidence signals
6. **Risk Assessment**: 8-layer risk management filters
7. **Execution**: Places bracket orders (entry + SL + TP)
8. **Monitoring**: Continuous position monitoring with trailing stops

### Profit Optimization Techniques
- **Dynamic Leverage**: Higher in low volatility, lower in high volatility
- **Kelly Sizing**: Optimal bet sizing based on edge
- **Trailing Stops**: Lock in profits as price moves favorably
- **Quick Scalps**: Target 0.5-2% moves with 1:3 risk/reward
- **Multi-Strategy Confirmation**: Requires 2+ strategies to agree
- **AI Consensus**: Reduces false signals through LLM validation

---

## Database Schema

- **trading_pairs**: Monitored coins with scores & metrics
- **trades**: Full trade lifecycle with indicators snapshot
- **performance_metrics**: Daily/weekly performance tracking
- **ai_decisions**: AI model decision log for audit
- **market_data**: Cached OHLCV data
- **strategy_performance**: Strategy performance by market regime

---

## Performance Targets

| Metric | Conservative | Target | Aggressive |
|--------|-------------|--------|------------|
| Daily Return | 2-5% | 5-20% | 20-100%+ |
| Win Rate | 55%+ | 60%+ | 65%+ |
| Profit Factor | 1.5+ | 2.0+ | 2.5+ |
| Max Drawdown | <10% | <15% | <20% |
| Sharpe Ratio | >1.5 | >2.0 | >3.0 |

> ⚠️ **Reality Check**: 2x-10x daily returns (200-1000%) are extremely unlikely and would require taking on extreme risk. The system is designed to pursue aggressive growth while managing risk through multiple safeguards. Actual returns will vary significantly and losses are possible.

---

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest

# Code formatting
black .
isort .

# Type checking
mypy .
```

---

## License

MIT License - See LICENSE file for details

---

## Disclaimer

This software is for educational and research purposes. The authors are not responsible for any financial losses. Cryptocurrency trading is highly speculative and risky. Always do your own research and consult with a financial advisor before trading.
