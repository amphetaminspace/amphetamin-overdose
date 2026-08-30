"""
amphetamin_Overdose - Fully Automated Crypto Trading System
============================================================
Entry point for the trading engine.

Usage:
    python main.py                  # Start trading engine
    python main.py --backtest       # Run backtest
    python main.py --scan           # Scan and rank pairs only
    python main.py --status         # Show current status
    python main.py --optimize       # Run optimization only
"""
import asyncio
import argparse
import sys
from loguru import logger

from core.engine import engine
from data.database import db
from config.settings import settings
from portfolio.manager import portfolio_manager


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "logs/amphetamin_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        compression="gz",
    )


async def run_trading():
    """Run the main trading loop."""
    setup_logging()
    await engine.initialize()
    await engine.run()


async def run_backtest():
    """Run backtesting mode."""
    setup_logging()
    logger.info("Starting backtest mode...")

    from backtesting.backtester import Backtester
    db.create_tables()

    bt = Backtester()
    results = await bt.run(
        symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=10000,
    )

    logger.info(f"Backtest Results:")
    logger.info(f"  Total Return: {results['total_return_pct']:+.2f}%")
    logger.info(f"  Total Trades: {results['total_trades']}")
    logger.info(f"  Win Rate: {results['win_rate']:.1%}")
    logger.info(f"  Profit Factor: {results['profit_factor']:.2f}")
    logger.info(f"  Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    logger.info(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")


async def run_scan():
    """Scan and rank pairs."""
    setup_logging()
    db.create_tables()
    await engine.initialize()
    pairs = await portfolio_manager.scan_and_rank_pairs()

    logger.info(f"\nTop {len(pairs)} Trading Pairs:")
    logger.info("-" * 80)
    for i, pair in enumerate(pairs, 1):
        logger.info(
            f"  {i:2d}. {pair['symbol']:<12} | "
            f"Volume: ${pair['volume_24h']:>12,.0f} | "
            f"Change: {pair['change_24h']:>+6.2f}% | "
            f"Score: {pair['opportunity_score']:>5.1f}"
        )


async def show_status():
    """Show current system status."""
    setup_logging()
    db.create_tables()
    await engine.initialize()

    status = engine.get_status()
    logger.info("\n" + "=" * 60)
    logger.info("  amphetamin_Overdose - System Status")
    logger.info("=" * 60)
    logger.info(f"  Running: {status['running']}")
    logger.info(f"  Mode: {'PAPER' if status['paper_trading'] else 'LIVE'}")
    logger.info(f"  Total Trades: {status['total_trades']}")
    logger.info(f"  Win Rate: {status['win_rate']:.1%}")
    logger.info(f"  Total P&L: {status['total_pnl_pct']:+.2f}%")
    logger.info(f"  Open Positions: {status['open_positions']}")
    logger.info(f"  Watchlist: {status['watchlist_size']} pairs")

    if status['daily_stats']:
        ds = status['daily_stats']
        logger.info(f"\n  Daily Stats:")
        logger.info(f"    P&L: ${ds['daily_pnl']:+.2f}")
        logger.info(f"    Trades: {ds['daily_trades']}")
        logger.info(f"    Win Rate: {ds['win_rate']:.1%}")
        logger.info(f"    Win Streak: {ds['win_streak']}")
        logger.info(f"    Loss Streak: {ds['loss_streak']}")

    if status['learning_stats']:
        ls = status['learning_stats']
        logger.info(f"\n  Learning:")
        logger.info(f"    Total Trades Analyzed: {ls.get('total_trades', 0)}")
        logger.info(f"    Win Rate: {ls.get('win_rate', 0):.1%}")
        logger.info(f"    Profit Factor: {ls.get('profit_factor', 0):.2f}")
        logger.info(f"    Model Trained: {ls.get('model_trained', False)}")


async def run_optimize():
    """Run optimization only."""
    setup_logging()
    db.create_tables()
    await engine.initialize()
    await engine._run_optimization()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="amphetamin_Overdose - Automated Crypto Trading System"
    )
    parser.add_argument(
        "--mode",
        choices=["trade", "backtest", "scan", "status", "optimize"],
        default="trade",
        help="Operating mode",
    )
    parser.add_argument("--paper", action="store_true", help="Force paper trading")
    parser.add_argument("--live", action="store_true", help="Force live trading")

    args = parser.parse_args()

    if args.paper:
        settings.paper_trading = True
    if args.live:
        settings.paper_trading = False

    if args.mode == "trade":
        asyncio.run(run_trading())
    elif args.mode == "backtest":
        asyncio.run(run_backtest())
    elif args.mode == "scan":
        asyncio.run(run_scan())
    elif args.mode == "status":
        asyncio.run(show_status())
    elif args.mode == "optimize":
        asyncio.run(run_optimize())


if __name__ == "__main__":
    main()
