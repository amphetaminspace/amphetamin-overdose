"""
Portfolio Manager.
Manages position tracking, allocation, and pair selection.
"""
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from data.database import db, TradingPair, Trade, TradeStatus, TradeDirection
from data.market_data import market_fetcher
from config.settings import settings


@dataclass
class Position:
    """Active position tracking."""
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    leverage: float
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    entry_time: datetime = field(default_factory=datetime.utcnow)
    unrealized_pnl: float = 0.0
    strategy: str = ""


class PortfolioManager:
    """Manages the portfolio of positions and pair selection."""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.watchlist: List[str] = []
        self.blacklist: List[str] = []

    async def initialize(self):
        """Initialize portfolio from database."""
        session = db.get_session()
        try:
            # Load active pairs
            pairs = db.get_active_pairs(session)
            self.watchlist = [p.symbol for p in pairs]

            # Load open trades
            open_trades = db.get_open_trades(session)
            for trade in open_trades:
                self.positions[trade.symbol] = Position(
                    symbol=trade.symbol,
                    direction=trade.direction.value,
                    entry_price=trade.entry_price,
                    quantity=trade.position_size,
                    leverage=trade.leverage,
                    stop_loss=trade.stop_loss or 0,
                    take_profit=trade.take_profit or 0,
                    strategy=trade.strategy_used or "",
                )

            logger.info(f"Portfolio initialized: {len(self.positions)} open positions, {len(self.watchlist)} pairs")
        finally:
            session.close()

    async def scan_and_rank_pairs(self) -> List[Dict]:
        """
        Scan market for best trading pairs.
        Ranks by volume, volatility, spread, and opportunity score.
        """
        # Get top volume pairs from exchange
        top_pairs = await market_fetcher.get_top_volume_pairs(limit=50)

        if not top_pairs:
            logger.warning("No pairs found from market scan")
            return []

        # Filter and rank
        scored_pairs = []
        for pair in top_pairs:
            # Skip blacklisted
            if pair["symbol"] in self.blacklist:
                continue

            # Skip low volume
            if pair["volume_24h"] < 1_000_000:  # Min $1M daily volume
                continue

            # Skip high spread
            if pair["spread_pct"] > 0.5:  # Max 0.5% spread
                continue

            # Calculate opportunity score
            score = self._calculate_opportunity_score(pair)
            scored_pairs.append({
                **pair,
                "opportunity_score": score,
            })

        # Sort by score
        scored_pairs.sort(key=lambda x: x["opportunity_score"], reverse=True)

        # Take top N
        top = scored_pairs[:settings.max_pairs]

        # Update database
        session = db.get_session()
        try:
            for pair in top:
                db.upsert_pair(
                    session,
                    symbol=pair["symbol"],
                    volume_24h=pair["volume_24h"],
                    spread_pct=pair["spread_pct"],
                    current_score=pair["opportunity_score"],
                    is_active=True,
                )
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update pairs in DB: {e}")
        finally:
            session.close()

        self.watchlist = [p["symbol"] for p in top]
        logger.info(f"Scanned and ranked pairs. Top {len(top)} selected.")
        return top

    def _calculate_opportunity_score(self, pair: Dict) -> float:
        """
        Calculate opportunity score for a pair.
        Higher = better trading opportunity.
        """
        score = 0.0

        # Volume score (0-30 points) - higher volume = better
        vol = pair.get("volume_24h", 0)
        if vol > 100_000_000:
            score += 30
        elif vol > 50_000_000:
            score += 25
        elif vol > 10_000_000:
            score += 20
        elif vol > 5_000_000:
            score += 15
        elif vol > 1_000_000:
            score += 10
        else:
            score += 5

        # Spread score (0-20 points) - lower spread = better
        spread = pair.get("spread_pct", 1)
        if spread < 0.05:
            score += 20
        elif spread < 0.1:
            score += 15
        elif spread < 0.2:
            score += 10
        elif spread < 0.5:
            score += 5

        # Momentum score (0-25 points)
        change = abs(pair.get("change_24h", 0))
        if 2 < change < 10:  # Good momentum without being overextended
            score += 25
        elif 1 < change < 15:
            score += 15
        elif change >= 15:
            score += 5  # Too extended

        # Volatility bonus (0-25 points) - we want some volatility for scalping
        # (estimated from daily range)
        if 3 < change < 8:
            score += 25
        elif 1.5 < change < 12:
            score += 15
        elif change >= 12:
            score += 5

        return score

    def add_position(self, position: Position):
        """Add a new position."""
        self.positions[position.symbol] = position
        logger.info(f"Added position: {position.symbol} {position.direction} @ {position.entry_price}")

    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a position."""
        return self.positions.pop(symbol, None)

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a position by symbol."""
        return self.positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in a symbol."""
        return symbol in self.positions

    def get_total_exposure(self) -> float:
        """Get total portfolio exposure."""
        return sum(
            pos.quantity * pos.entry_price * pos.leverage
            for pos in self.positions.values()
        )

    def get_open_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.positions)

    def get_available_slots(self) -> int:
        """Get remaining position slots."""
        return settings.max_open_positions - len(self.positions)

    def blacklist_pair(self, symbol: str, reason: str = ""):
        """Add a pair to blacklist."""
        if symbol not in self.blacklist:
            self.blacklist.append(symbol)
            logger.info(f"Blacklisted {symbol}: {reason}")

    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary."""
        return {
            "total_positions": len(self.positions),
            "total_exposure": self.get_total_exposure(),
            "watchlist_size": len(self.watchlist),
            "available_slots": self.get_available_slots(),
            "positions": [
                {
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "entry_price": p.entry_price,
                    "leverage": p.leverage,
                    "unrealized_pnl": p.unrealized_pnl,
                    "strategy": p.strategy,
                }
                for p in self.positions.values()
            ],
        }


portfolio_manager = PortfolioManager()
