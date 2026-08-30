"""
Backtesting Engine.
Tests strategies on historical data before risking real capital.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from loguru import logger

from data.market_data import market_fetcher
from indicators.technical import indicators
from strategies.scalping import scalping_engine
from risk.risk_manager import RiskManager, PortfolioState


class Backtester:
    """Historical backtesting engine."""

    async def run(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 10000,
    ) -> Dict:
        """Run backtest on historical data."""
        logger.info(f"Starting backtest: {start_date} to {end_date}")
        logger.info(f"Symbols: {symbols}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")

        await market_fetcher.initialize()

        results = {
            "total_return_pct": 0,
            "total_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0,
            "trades": [],
        }

        all_trades = []

        for symbol in symbols:
            logger.info(f"Backtesting {symbol}...")

            # Fetch historical data
            df = await market_fetcher.fetch_ohlcv(
                symbol, timeframe="1m", limit=10000
            )

            if df.empty:
                logger.warning(f"No data for {symbol}")
                continue

            # Run strategy on each candle
            trades = self._simulate_trades(df, symbol, initial_capital)
            all_trades.extend(trades)

        # Calculate results
        if all_trades:
            results["total_trades"] = len(all_trades)
            winners = [t for t in all_trades if t["pnl_pct"] > 0]
            losers = [t for t in all_trades if t["pnl_pct"] <= 0]

            results["win_rate"] = len(winners) / len(all_trades)

            total_win = sum(t["pnl_pct"] for t in winners) if winners else 0
            total_loss = abs(sum(t["pnl_pct"] for t in losers)) if losers else 1
            results["profit_factor"] = total_win / total_loss if total_loss > 0 else float("inf")

            results["total_return_pct"] = sum(t["pnl_pct"] for t in all_trades)

            # Max drawdown
            cumulative = np.cumsum([t["pnl_pct"] for t in all_trades])
            peak = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - peak)
            results["max_drawdown_pct"] = abs(min(drawdown)) if len(drawdown) > 0 else 0

            # Sharpe ratio
            returns = [t["pnl_pct"] for t in all_trades]
            if len(returns) > 1:
                results["sharpe_ratio"] = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252)

            results["trades"] = all_trades

        await market_fetcher.close()
        return results

    def _simulate_trades(self, df: pd.DataFrame, symbol: str, capital: float) -> List[Dict]:
        """Simulate trades on historical data."""
        trades = []
        in_position = False
        entry_price = 0
        direction = ""

        # Iterate through data with a window
        for i in range(200, len(df) - 1, 5):  # Every 5 candles
            window = df.iloc[:i]

            if not in_position:
                # Look for entry signal
                signal = scalping_engine.generate_signal(
                    df=window,
                    symbol=symbol,
                    current_capital=capital,
                    max_leverage=10,
                    risk_per_trade=0.02,
                )

                if signal and signal.confidence > 0.6:
                    in_position = True
                    entry_price = signal.entry_price
                    direction = signal.direction
                    stop_loss = signal.stop_loss
                    take_profit = signal.take_profit
                    leverage = signal.leverage

            else:
                # Check exit conditions
                current_price = df.iloc[i]["close"]
                exit_reason = None

                if direction == "long":
                    if current_price <= stop_loss:
                        exit_reason = "stop_loss"
                    elif current_price >= take_profit:
                        exit_reason = "take_profit"
                else:
                    if current_price >= stop_loss:
                        exit_reason = "stop_loss"
                    elif current_price <= take_profit:
                        exit_reason = "take_profit"

                # Also exit after 30 candles (time-based)
                if not exit_reason and i % 30 == 0:
                    exit_reason = "time_exit"

                if exit_reason:
                    if direction == "long":
                        pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage

                    trades.append({
                        "symbol": symbol,
                        "direction": direction,
                        "entry_price": entry_price,
                        "exit_price": current_price,
                        "pnl_pct": pnl_pct,
                        "exit_reason": exit_reason,
                        "leverage": leverage,
                    })

                    in_position = False

        return trades
