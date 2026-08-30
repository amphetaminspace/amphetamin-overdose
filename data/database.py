"""
PostgreSQL database layer with SQLAlchemy ORM.
Stores trading pairs, trades, performance metrics, and AI decisions.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, Index, JSON, BigInteger, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool
import enum

from config.settings import settings

Base = declarative_base()
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine)


# ── Enums ──────────────────────────────────────────────
class TradeStatus(enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


class TradeDirection(enum.Enum):
    LONG = "long"
    SHORT = "short"


class SignalStrength(enum.Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


# ── Models ─────────────────────────────────────────────
class TradingPair(Base):
    """Tracks coins being monitored and traded."""
    __tablename__ = "trading_pairs"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    exchange = Column(String(20), nullable=False, default="binance")
    base_asset = Column(String(10))
    quote_asset = Column(String(10), default="USDT")
    is_active = Column(Boolean, default=True)
    is_tradable = Column(Boolean, default=True)
    max_leverage = Column(Float, default=25.0)
    current_score = Column(Float, default=0.0)  # AI-assigned opportunity score
    volatility_24h = Column(Float, default=0.0)
    volume_24h = Column(Float, default=0.0)
    spread_pct = Column(Float, default=0.0)
    avg_daily_range = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    last_evaluated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)

    trades = relationship("Trade", back_populates="pair")

    __table_args__ = (
        Index("idx_pair_active_score", "is_active", "current_score"),
    )


class Trade(Base):
    """Individual trade records with full lifecycle tracking."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    pair_id = Column(Integer, ForeignKey("trading_pairs.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(TradeDirection), nullable=False)
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING)

    # Entry
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, default=datetime.utcnow)
    position_size = Column(Float, nullable=False)  # in base currency
    leverage = Column(Float, default=1.0)
    margin_used = Column(Float, nullable=False)

    # Exit
    exit_price = Column(Float)
    exit_time = Column(DateTime)
    exit_reason = Column(String(50))  # take_profit, stop_loss, trailing_stop, signal_reversal, manual

    # P&L
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    pnl_usd = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    funding_rate = Column(Float, default=0.0)

    # Risk Management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    trailing_stop = Column(Float)
    trailing_stop_activated = Column(Boolean, default=False)

    # Signal Data
    signal_strength = Column(Enum(SignalStrength))
    strategy_used = Column(String(50))
    indicators_snapshot = Column(JSON)  # snapshot of all indicators at entry
    ai_confidence = Column(Float, default=0.0)
    ai_analysis = Column(Text)

    # Learning
    was_winner = Column(Boolean)
    lessons_learned = Column(Text)
    market_regime = Column(String(20))  # trending, ranging, volatile, calm

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pair = relationship("TradingPair", back_populates="trades")

    __table_args__ = (
        Index("idx_trade_status_time", "status", "entry_time"),
        Index("idx_trade_symbol_time", "symbol", "entry_time"),
    )


class PerformanceMetrics(Base):
    """Daily/weekly performance tracking."""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    period = Column(String(10), nullable=False)  # daily, weekly, monthly

    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)

    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    avg_trade_duration = Column(Float, default=0.0)  # minutes

    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    calmar_ratio = Column(Float, default=0.0)

    expectancy = Column(Float, default=0.0)
    kelly_criterion = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class AIDecision(Base):
    """Log of AI model decisions for audit and learning."""
    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    model = Column(String(30), nullable=False)  # longcat, gemini, ml_ensemble
    symbol = Column(String(20), nullable=False)
    decision = Column(String(20), nullable=False)  # buy, sell, hold
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text)
    indicators_used = Column(JSON)
    market_context = Column(JSON)
    outcome = Column(String(20))  # correct, incorrect, pending
    pnl_result = Column(Float)


class MarketData(Base):
    """Cached OHLCV data for analysis."""
    __tablename__ = "market_data"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_market_data_symbol_tf_time", "symbol", "timeframe", "timestamp", unique=True),
    )


class StrategyPerformance(Base):
    """Tracks which strategies perform best in which conditions."""
    __tablename__ = "strategy_performance"

    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(50), nullable=False, index=True)
    market_regime = Column(String(20), nullable=False)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_pnl_pct = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


# ── Database Manager ───────────────────────────────────
class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.Session = SessionLocal

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.Session()

    def upsert_pair(self, session, symbol: str, **kwargs) -> TradingPair:
        pair = session.query(TradingPair).filter_by(symbol=symbol).first()
        if pair:
            for k, v in kwargs.items():
                setattr(pair, k, v)
            pair.last_evaluated = datetime.utcnow()
        else:
            pair = TradingPair(symbol=symbol, **kwargs)
            session.add(pair)
        session.flush()
        return pair

    def get_active_pairs(self, session) -> List[TradingPair]:
        return session.query(TradingPair).filter_by(is_active=True, is_tradable=True).all()

    def log_trade(self, session, **kwargs) -> Trade:
        trade = Trade(**kwargs)
        session.add(trade)
        session.flush()
        return trade

    def update_trade(self, session, trade_id: int, **kwargs):
        trade = session.query(Trade).filter_by(id=trade_id).first()
        if trade:
            for k, v in kwargs.items():
                setattr(trade, k, v)
            trade.updated_at = datetime.utcnow()
            session.flush()
        return trade

    def get_open_trades(self, session) -> List[Trade]:
        return session.query(Trade).filter_by(status=TradeStatus.OPEN).all()

    def get_trades_for_learning(self, session, limit: int = 1000) -> List[Trade]:
        return (
            session.query(Trade)
            .filter(Trade.status == TradeStatus.CLOSED)
            .filter(Trade.was_winner.isnot(None))
            .order_by(Trade.exit_time.desc())
            .limit(limit)
            .all()
        )


db = DatabaseManager()
