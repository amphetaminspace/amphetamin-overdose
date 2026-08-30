"""
Main Trading Engine - amphetamin_Overdose
Orchestrates all components: data, analysis, signals, risk, execution.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from config.settings import settings
from data.database import db, TradeStatus, TradeDirection, SignalStrength
from data.market_data import market_fetcher
from indicators.technical import TechnicalIndicators, indicators
from strategies.scalping import ScalpingEngine, scalping_engine, TradingSignal
from ai.ai_integration import ai_ensemble, longcat_ai, gemini_ai
from risk.risk_manager import RiskManager, risk_manager, PortfolioState
from portfolio.manager import PortfolioManager, portfolio_manager, Position
from learning.learner import AdaptiveLearner, learner, TradeOutcome
from optimization.self_optimize import SelfOptimizer, self_optimizer
from exchanges.binance_client import binance_client, OrderResult


class TradingEngine:
    """
    The main trading engine that runs the full pipeline:
    1. Scan & rank pairs
    2. Fetch market data
    3. Compute indicators
    4. Generate signals
    5. AI validation
    6. Risk assessment
    7. Execute trades
    8. Monitor & manage positions
    9. Learn from outcomes
    10. Self-optimize
    """

    def __init__(self):
        self.is_running = False
        self.scan_interval = 60  # seconds between market scans
        self.monitor_interval = 10  # seconds between position monitoring
        self.optimization_interval = 1800  # seconds between optimization runs
        self.last_scan = None
        self.last_optimization = None
        self.trade_count = 0
        self.win_count = 0
        self.total_pnl = 0.0

    async def initialize(self):
        """Initialize all components."""
        logger.info("=" * 60)
        logger.info("  amphetamin_Overdose - Trading Engine Initializing")
        logger.info("=" * 60)

        # Create database tables
        db.create_tables()
        logger.info("Database initialized")

        # Connect to exchanges
        await market_fetcher.initialize()
        await binance_client.connect()

        # Initialize AI
        await ai_ensemble.initialize()

        # Initialize portfolio
        await portfolio_manager.initialize()

        logger.info("All components initialized successfully")
        logger.info(f"Mode: {'PAPER TRADING' if settings.paper_trading else 'LIVE TRADING'}")
        logger.info(f"Max pairs: {settings.max_pairs} | Max leverage: {settings.max_leverage}x")
        logger.info(f"Risk per trade: {settings.risk_per_trade*100}% | Daily loss limit: {settings.daily_loss_limit*100}%")

    async def run(self):
        """Main trading loop."""
        self.is_running = True
        logger.info("Trading engine STARTED")

        try:
            while self.is_running:
                # 1. Scan and rank pairs (every scan_interval)
                await self._scan_market()

                # 2. Analyze and trade
                await self._analyze_and_trade()

                # 3. Monitor open positions
                await self._monitor_positions()

                # 4. Self-optimize (every optimization_interval)
                await self._run_optimization()

                # 5. Wait before next cycle
                await asyncio.sleep(5)

        except KeyboardInterrupt:
            logger.info("Trading engine stopped by user")
        except Exception as e:
            logger.error(f"Trading engine error: {e}")
            raise
        finally:
            await self.shutdown()

    async def _scan_market(self):
        """Scan market for best pairs."""
        now = datetime.utcnow()
        if self.last_scan and (now - self.last_scan).seconds < self.scan_interval:
            return

        self.last_scan = now
        logger.info("Scanning market for opportunities...")

        # Scan and rank pairs
        top_pairs = await portfolio_manager.scan_and_rank_pairs()
        logger.info(f"Found {len(top_pairs)} tradable pairs")

    async def _analyze_and_trade(self):
        """Analyze watchlist and execute trades."""
        if not portfolio_manager.watchlist:
            return

        # Check if we can open more positions
        if portfolio_manager.get_available_slots() <= 0:
            return

        # Fetch data for all watchlist pairs
        data = await market_fetcher.fetch_multiple_ohlcv(
            portfolio_manager.watchlist[:10],  # Top 10 for analysis
            timeframe=settings.scalping_timeframe,
            limit=200,
        )

        for symbol, df in data.items():
            if portfolio_manager.has_position(symbol):
                continue

            # Generate signal
            signal = scalping_engine.generate_signal(
                df=df,
                symbol=symbol,
                current_capital=10000,  # Will be replaced with actual balance
                max_leverage=settings.max_leverage,
                risk_per_trade=settings.risk_per_trade,
            )

            if not signal:
                continue

            # Check confidence threshold
            if signal.confidence < self_optimizer.current_params.get("confidence_threshold", 0.55):
                continue

            # AI validation
            ai_signal = await self._validate_with_ai(symbol, signal, df)

            # Risk assessment
            portfolio_state = await self._get_portfolio_state()
            risk_assessment = risk_manager.assess_trade(
                signal_direction=signal.direction,
                signal_confidence=signal.confidence,
                position_size_pct=signal.position_size_pct,
                leverage=signal.leverage,
                current_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                portfolio=portfolio_state,
            )

            if not risk_assessment.approved:
                logger.warning(f"Trade rejected for {symbol}: {risk_assessment.reason}")
                continue

            # Execute trade
            await self._execute_trade(signal, risk_assessment)

    async def _validate_with_ai(
        self, symbol: str, signal: TradingSignal, df
    ) -> Optional[Dict]:
        """Validate signal with AI ensemble."""
        try:
            # Get indicator snapshot
            snapshot = indicators.compute_all(df)
            indicator_dict = snapshot.to_dict()

            # Get AI consensus
            ai_result = await ai_ensemble.get_consensus_signal(
                symbol=symbol,
                indicators=indicator_dict,
                market_context={
                    "volume_24h": 0,  # Would be populated from ticker
                    "change_24h": 0,
                    "spread_pct": 0,
                    "volatility_regime": snapshot.volatility_regime,
                },
                ohlcv_data=df.tail(20).to_dict("records") if not df.empty else [],
            )

            if ai_result:
                logger.info(
                    f"AI validation for {symbol}: {ai_result.decision} "
                    f"(confidence: {ai_result.confidence:.0%})"
                )

                # If AI disagrees strongly, reduce confidence
                if ai_result.decision != signal.direction and ai_result.confidence > 0.7:
                    signal.confidence *= 0.7
                    signal.reasons.append(f"AI disagrees: {ai_result.reasoning[:100]}")

            return ai_result

        except Exception as e:
            logger.warning(f"AI validation failed for {symbol}: {e}")
            return None

    async def _execute_trade(self, signal: TradingSignal, risk_assessment):
        """Execute a trade with full risk management."""
        symbol = signal.symbol

        logger.info(f"Executing trade: {symbol} {signal.direction} @ {signal.entry_price}")
            logger.info(f"  Confidence: {signal.confidence:.0%} | Leverage: {risk_assessment.adjusted_leverage:.1f}x")
        logger.info(f"  SL: {signal.stop_loss:.4f} | TP: {signal.take_profit:.4f}")
        logger.info(f"  Strategy: {signal.strategy_name} | RR: {signal.risk_reward_ratio:.1f}")

        if settings.paper_trading:
            # Paper trading - simulate execution
            await self._simulate_trade(signal, risk_assessment)
        else:
            # Live trading
            await self._live_trade(signal, risk_assessment)

    async def _simulate_trade(self, signal: TradingSignal, risk_assessment):
        """Simulate a trade for paper trading."""
        # Calculate position size
        balance = 10000  # Simulated balance
        position_value = balance * risk_assessment.adjusted_size_pct
        quantity = position_value / signal.entry_price

        # Create position
        position = Position(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            quantity=quantity,
            leverage=risk_assessment.adjusted_leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy=signal.strategy_name,
        )
        portfolio_manager.add_position(position)

        # Log to database
        session = db.get_session()
        try:
            trade = db.log_trade(
                session,
                pair_id=1,  # Would be actual pair ID
                symbol=signal.symbol,
                direction=TradeDirection.LONG if signal.direction == "long" else TradeDirection.SHORT,
                status=TradeStatus.OPEN,
                entry_price=signal.entry_price,
                position_size=quantity,
                leverage=risk_assessment.adjusted_leverage,
                margin_used=position_value,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                signal_strength=SignalStrength.STRONG if signal.confidence > 0.8 else SignalStrength.MODERATE,
                strategy_used=signal.strategy_name,
                indicators_snapshot=signal.indicators_snapshot,
                ai_confidence=signal.confidence,
                ai_analysis=" | ".join(signal.reasons),
            )
            session.commit()
            logger.info(f"Paper trade logged: {symbol} (ID: {trade.id})")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log paper trade: {e}")
        finally:
            session.close()

    async def _live_trade(self, signal: TradingSignal, risk_assessment):
        """Execute a live trade on Binance."""
        # Get account balance
        balance_info = await binance_client.get_account_balance()
        balance = balance_info.get("available", 0)

        # Calculate position size
        position_value = balance * risk_assessment.adjusted_size_pct
        quantity = position_value / signal.entry_price

        # Place bracket order
        side = "buy" if signal.direction == "long" else "sell"
        results = await binance_client.place_bracket_order(
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            leverage=risk_assessment.adjusted_leverage,
        )

        if results["entry"].success:
            position = Position(
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=signal.entry_price,
                quantity=quantity,
                leverage=risk_assessment.adjusted_leverage,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy=signal.strategy_name,
            )
            portfolio_manager.add_position(position)
            logger.info(f"Live trade executed: {signal.symbol}")
        else:
            logger.error(f"Trade execution failed: {results['entry'].error}")

    async def _monitor_positions(self):
        """Monitor and manage open positions."""
        if not portfolio_manager.positions:
            return

        for symbol, position in list(portfolio_manager.positions.items()):
            # Fetch current price
            ticker = await market_fetcher.fetch_ticker(symbol)
            if not ticker:
                continue

            current_price = ticker.get("last", 0)
            if current_price == 0:
                continue

            # Calculate unrealized P&L
            if position.direction == "long":
                pnl_pct = (current_price - position.entry_price) / position.entry_price * 100
            else:
                pnl_pct = (position.entry_price - current_price) / position.entry_price * 100

            pnl_pct *= position.leverage
            position.unrealized_pnl = pnl_pct

            # Check stop loss
            if position.direction == "long" and current_price <= position.stop_loss:
                await self._close_position(symbol, current_price, "stop_loss")
                continue
            elif position.direction == "short" and current_price >= position.stop_loss:
                await self._close_position(symbol, current_price, "stop_loss")
                continue

            # Check take profit
            if position.direction == "long" and current_price >= position.take_profit:
                await self._close_position(symbol, current_price, "take_profit")
                continue
            elif position.direction == "short" and current_price <= position.take_profit:
                await self._close_position(symbol, current_price, "take_profit")
                continue

            # Trailing stop logic
            await self._check_trailing_stop(position, current_price)

    async def _check_trailing_stop(self, position: Position, current_price: float):
        """Update and check trailing stop."""
        activation_price = position.entry_price * (1 + self_optimizer.current_params["trailing_activation_pct"])

        if position.direction == "long":
            if current_price >= activation_price:
                new_stop = current_price * (1 - self_optimizer.current_params["stop_loss_atr_mult"] * 0.01)
                if position.trailing_stop is None or new_stop > position.trailing_stop:
                    position.trailing_stop = new_stop
                    logger.info(f"Trailing stop updated for {position.symbol}: {new_stop:.4f}")

                if current_price <= position.trailing_stop:
                    await self._close_position(position.symbol, current_price, "trailing_stop")
        else:
            if current_price <= activation_price:
                new_stop = current_price * (1 + self_optimizer.current_params["stop_loss_atr_mult"] * 0.01)
                if position.trailing_stop is None or new_stop < position.trailing_stop:
                    position.trailing_stop = new_stop

                if current_price >= position.trailing_stop:
                    await self._close_position(position.symbol, current_price, "trailing_stop")

    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position and record the outcome."""
        position = portfolio_manager.get_position(symbol)
        if not position:
            return

        # Calculate P&L
        if position.direction == "long":
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100

        pnl_pct *= position.leverage
        pnl_usd = position.quantity * position.entry_price * (pnl_pct / 100)

        # Update risk manager
        risk_manager.update_after_trade(pnl_usd)

        # Record for learning
        outcome = TradeOutcome(
            trade_id=0,
            symbol=symbol,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=exit_price,
            pnl_pct=pnl_pct,
            indicators_at_entry={},
            market_regime="unknown",
            strategy=position.strategy,
            was_winner=pnl_pct > 0,
            duration_minutes=0,
        )
        learner.record_trade(outcome)

        # Remove from portfolio
        portfolio_manager.remove_position(symbol)

        # Close on exchange if live
        if not settings.paper_trading:
            await binance_client.close_position(symbol)

        # Log
        self.trade_count += 1
        if pnl_pct > 0:
            self.win_count += 1
        self.total_pnl += pnl_pct

        logger.info(
            f"Position closed: {symbol} | Reason: {reason} | "
            f"P&L: {pnl_pct:+.2f}% (${pnl_usd:+.2f}) | "
            f"Total trades: {self.trade_count} | Win rate: {self.win_count/max(self.trade_count,1):.0%}"
        )

    async def _get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state."""
        if settings.paper_trading:
            balance = 10000 + self.total_pnl
        else:
            balance_info = await binance_client.get_account_balance()
            balance = balance_info.get("total_equity", 10000)

        positions = await binance_client.get_positions() if not settings.paper_trading else []
        total_exposure = sum(p.quantity * p.entry_price * p.leverage for p in positions)

        return PortfolioState(
            total_equity=balance,
            available_margin=balance - total_exposure,
            used_margin=total_exposure,
            unrealized_pnl=sum(p.unrealized_pnl for p in positions),
            realized_pnl_today=risk_manager.daily_pnl,
            open_positions=len(positions),
            total_exposure=total_exposure,
            margin_level=balance / max(total_exposure, 1),
            daily_return_pct=self.total_pnl / 10000 * 100,
            max_drawdown_current=risk_manager.current_drawdown,
            win_streak=risk_manager.win_streak,
            loss_streak=risk_manager.loss_streak,
        )

    async def _run_optimization(self):
        """Run self-optimization cycle."""
        now = datetime.utcnow()
        if self.last_optimization and (now - self.last_optimization).seconds < self.optimization_interval:
            return

        self.last_optimization = now

        # Train learning model
        if len(learner.trade_outcomes) >= learner.min_training_samples:
            learner.train_model()
            learner.generate_insights()

        # Run self-optimization
        changes = await self_optimizer.optimize()

        if changes:
            logger.info(f"Self-optimization complete: {len(changes)} changes")

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down trading engine...")
        self.is_running = False

        # Close all positions if live
        if not settings.paper_trading:
            for symbol in list(portfolio_manager.positions.keys()):
                await binance_client.close_position(symbol)

        # Close connections
        await market_fetcher.close()
        await binance_client.close()

        # Save learning model
        learner.save_model()

        logger.info("Trading engine shut down complete")
        logger.info(f"Session stats: {self.trade_count} trades, {self.win_count} wins, {self.total_pnl:+.2f}% total P&L")

    def get_status(self) -> Dict:
        """Get engine status."""
        return {
            "running": self.is_running,
            "paper_trading": settings.paper_trading,
            "total_trades": self.trade_count,
            "win_count": self.win_count,
            "win_rate": self.win_count / max(self.trade_count, 1),
            "total_pnl_pct": self.total_pnl,
            "open_positions": len(portfolio_manager.positions),
            "watchlist_size": len(portfolio_manager.watchlist),
            "daily_stats": risk_manager.get_daily_stats(),
            "learning_stats": learner.get_performance_summary(),
            "optimization": self_optimizer.get_optimization_summary(),
        }


engine = TradingEngine()
