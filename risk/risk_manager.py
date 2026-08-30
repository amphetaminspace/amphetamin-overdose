"""
Advanced Risk Management System.
Protects capital while allowing aggressive growth.
Implements multiple layers of protection.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings


@dataclass
class RiskAssessment:
    """Result of risk evaluation for a potential trade."""
    approved: bool
    reason: str
    adjusted_size_pct: float
    adjusted_leverage: float
    max_loss_usd: float
    risk_score: float  # 0-100, higher = riskier
    warnings: List[str] = field(default_factory=list)


@dataclass
class PortfolioState:
    """Current state of the portfolio."""
    total_equity: float
    available_margin: float
    used_margin: float
    unrealized_pnl: float
    realized_pnl_today: float
    open_positions: int
    total_exposure: float
    margin_level: float  # equity / used margin
    daily_return_pct: float
    max_drawdown_current: float
    win_streak: int
    loss_streak: int


class RiskManager:
    """
    Multi-layered risk management:
    1. Position sizing (Kelly Criterion + volatility adjustment)
    2. Portfolio exposure limits
    3. Correlation risk (avoid correlated positions)
    4. Drawdown protection (reduce size after losses)
    5. Daily loss limits (circuit breaker)
    6. Leverage management
    7. Streak protection (after consecutive losses)
    """

    def __init__(self):
        self.daily_pnl: float = 0.0
        self.daily_trades: int = 0
        self.daily_wins: int = 0
        self.daily_losses: int = 0
        self.peak_equity: float = 0.0
        self.current_drawdown: float = 0.0
        self.win_streak: int = 0
        self.loss_streak: int = 0
        self.last_reset_date: datetime = datetime.utcnow().date()
        self.trade_history_today: List[Dict] = []
        self._consecutive_loss_limit = 3
        self._consecutive_win_limit = 5

    def reset_daily(self):
        """Reset daily tracking."""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.last_reset_date = datetime.utcnow().date()
        self.trade_history_today = []
        logger.info("Daily risk metrics reset")

    def update_after_trade(self, pnl: float):
        """Update risk state after a trade closes."""
        self.daily_pnl += pnl
        self.daily_trades += 1

        if pnl > 0:
            self.daily_wins += 1
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.daily_losses += 1
            self.loss_streak += 1
            self.win_streak = 0

        # Update peak equity and drawdown
        if self.peak_equity > 0:
            self.current_drawdown = (self.peak_equity - (self.peak_equity + self.daily_pnl)) / self.peak_equity
        else:
            self.current_drawdown = 0

        self.trade_history_today.append({
            "pnl": pnl,
            "time": datetime.utcnow(),
            "cumulative_pnl": self.daily_pnl,
        })

    def assess_trade(
        self,
        signal_direction: str,
        signal_confidence: float,
        position_size_pct: float,
        leverage: float,
        current_price: float,
        stop_loss: float,
        portfolio: PortfolioState,
    ) -> RiskAssessment:
        """
        Full risk assessment for a potential trade.
        Returns approval status with adjustments.
        """
        warnings = []
        risk_score = 0

        # ── Layer 1: Daily Loss Limit (Circuit Breaker) ────
        if self.daily_pnl <= -portfolio.total_equity * settings.daily_loss_limit:
            return RiskAssessment(
                approved=False,
                reason=f"Daily loss limit reached: ${self.daily_pnl:.2f} (limit: {settings.daily_loss_limit*100:.1f}%)",
                adjusted_size_pct=0,
                adjusted_leverage=0,
                max_loss_usd=0,
                risk_score=100,
                warnings=["CIRCUIT BREAKER: Daily loss limit triggered"],
            )

        # ── Layer 2: Max Drawdown Protection ───────────────
        if self.current_drawdown >= settings.max_drawdown_pct:
            return RiskAssessment(
                approved=False,
                reason=f"Max drawdown reached: {self.current_drawdown*100:.1f}%",
                adjusted_size_pct=0,
                adjusted_leverage=0,
                max_loss_usd=0,
                risk_score=100,
                warnings=["CIRCUIT BREAKER: Max drawdown triggered"],
            )

        # ── Layer 3: Loss Streak Protection ─────────────────
        adjusted_size = position_size_pct
        adjusted_leverage = leverage

        if self.loss_streak >= self._consecutive_loss_limit:
            adjusted_size *= 0.5  # Halve position size
            adjusted_leverage = min(adjusted_leverage, 5.0)
            risk_score += 20
            warnings.append(f"Loss streak ({self.loss_streak}): Reducing position size by 50%")

        if self.loss_streak >= self._consecutive_loss_limit + 2:
            return RiskAssessment(
                approved=False,
                reason=f"Too many consecutive losses ({self.loss_streak}). Pausing trading.",
                adjusted_size_pct=0,
                adjusted_leverage=0,
                max_loss_usd=0,
                risk_score=90,
                warnings=["TRADING PAUSED: Excessive consecutive losses"],
            )

        # ── Layer 4: Win Streak (Take some profits) ────────
        if self.win_streak >= self._consecutive_win_limit:
            adjusted_size *= 0.75  # Reduce slightly to lock in gains
            risk_score += 5
            warnings.append(f"Win streak ({self.win_streak}): Slightly reducing size to protect gains")

        # ── Layer 5: Portfolio Exposure Limits ──────────────
        if portfolio.open_positions >= settings.max_open_positions:
            return RiskAssessment(
                approved=False,
                reason=f"Max open positions reached ({portfolio.open_positions}/{settings.max_open_positions})",
                adjusted_size_pct=0,
                adjusted_leverage=0,
                max_loss_usd=0,
                risk_score=80,
                warnings=["Max positions limit reached"],
            )

        # Total exposure check
        max_exposure = portfolio.total_equity * 3  # Max 3x total exposure
        new_exposure = (position_size_pct * portfolio.total_equity * adjusted_leverage)
        if portfolio.total_exposure + new_exposure > max_exposure:
            # Scale down to fit
            available_exposure = max_exposure - portfolio.total_exposure
            if available_exposure <= 0:
                return RiskAssessment(
                    approved=False,
                    reason="Max portfolio exposure reached",
                    adjusted_size_pct=0,
                    adjusted_leverage=0,
                    max_loss_usd=0,
                    risk_score=75,
                    warnings=["Portfolio exposure limit reached"],
                )
            adjusted_size = available_exposure / (portfolio.total_equity * adjusted_leverage)
            warnings.append("Position sized down to respect exposure limits")

        # ── Layer 6: Margin Level Protection ────────────────
        if portfolio.margin_level < 2.0:  # Margin call danger zone
            adjusted_size *= 0.3
            adjusted_leverage = min(adjusted_leverage, 3.0)
            risk_score += 30
            warnings.append("Low margin level: Significantly reducing size")

        # ── Layer 7: Leverage Adjustment ────────────────────
        # Scale leverage based on confidence
        if signal_confidence > 0.8:
            # High confidence: allow up to max leverage
            pass
        elif signal_confidence > 0.7:
            adjusted_leverage = min(adjusted_leverage, settings.max_leverage * 0.7)
        elif signal_confidence > 0.6:
            adjusted_leverage = min(adjusted_leverage, settings.max_leverage * 0.5)
        else:
            adjusted_leverage = min(adjusted_leverage, settings.max_leverage * 0.3)

        adjusted_leverage = min(adjusted_leverage, settings.max_leverage)

        # ── Layer 8: Volatility-based Risk Adjustment ──────
        risk_per_unit = abs(current_price - stop_loss) / current_price
        if risk_per_unit > 0.05:  # More than 5% stop distance
            adjusted_size *= 0.5
            risk_score += 15
            warnings.append("Wide stop loss: Reducing position size")

        # ── Calculate Max Loss ──────────────────────────────
        max_loss_usd = adjusted_size * portfolio.total_equity * risk_per_unit * adjusted_leverage
        max_loss_pct = max_loss_usd / portfolio.total_equity * 100

        # Ensure single trade risk is within limits
        if max_loss_pct > settings.risk_per_trade * 100 * 2:
            scale_down = (settings.risk_per_trade * 2) / (max_loss_pct / 100)
            adjusted_size *= scale_down
            max_loss_usd *= scale_down
            warnings.append("Position sized down to respect risk per trade limit")

        # ── Final Risk Score ────────────────────────────────
        risk_score += adjusted_leverage * 2  # Leverage adds risk
        risk_score += self.loss_streak * 10  # Consecutive losses add risk
        risk_score += max(0, (self.daily_losses - self.daily_wins)) * 5  # Daily performance adds risk
        risk_score = min(risk_score, 100)

        # ── Decision ────────────────────────────────────────
        approved = True
        reason = "Trade approved"

        if risk_score > 80:
            approved = False
            reason = "Risk score too high"
        elif risk_score > 60:
            warnings.append("ELEVATED RISK: Trade approved with caution")

        return RiskAssessment(
            approved=approved,
            reason=reason,
            adjusted_size_pct=adjusted_size,
            adjusted_leverage=adjusted_leverage,
            max_loss_usd=max_loss_usd,
            risk_score=risk_score,
            warnings=warnings,
        )

    def calculate_kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        kelly_fraction: float = 0.5,
    ) -> float:
        """
        Kelly Criterion for optimal position sizing.
        f* = (bp - q) / b
        where b = avg_win/avg_loss, p = win_rate, q = 1-p
        """
        if avg_loss == 0 or win_rate == 0:
            return settings.risk_per_trade

        b = avg_win / avg_loss  # Win/loss ratio
        p = win_rate
        q = 1 - p

        kelly = (b * p - q) / b

        # Use fractional Kelly for safety (half-Kelly)
        fractional_kelly = kelly * kelly_fraction

        # Clamp between 0.5% and 10% of capital
        return max(0.005, min(fractional_kelly, 0.10))

    def get_position_size_from_volatility(
        self,
        atr: float,
        price: float,
        portfolio_value: float,
        risk_pct: float = 0.02,
    ) -> float:
        """
        ATR-based position sizing.
        Risk a fixed % of portfolio per trade, sized by ATR.
        """
        risk_amount = portfolio_value * risk_pct
        atr_risk = atr * 1.5  # 1.5x ATR stop

        if atr_risk <= 0:
            return 0

        position_value = risk_amount / (atr_risk / price)
        position_pct = position_value / portfolio_value

        return min(position_pct, 0.15)  # Max 15% per trade

    def should_take_profits_early(
        self,
        current_pnl_pct: float,
        time_in_trade_minutes: int,
        market_regime: str,
    ) -> bool:
        """
        Dynamic profit-taking logic.
        Take profits earlier in choppy markets or after long holds.
        """
        # Quick scalp: take profit after 1% gain in under 5 minutes
        if current_pnl_pct >= 1.0 and time_in_trade_minutes <= 5:
            return True

        # In volatile markets, take profits at lower thresholds
        if market_regime in ("extreme", "high") and current_pnl_pct >= 2.0:
            return True

        # After 30 minutes, scale out
        if time_in_trade_minutes >= 30 and current_pnl_pct >= 1.5:
            return True

        return False

    def get_daily_stats(self) -> Dict:
        """Get daily risk statistics."""
        return {
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "daily_wins": self.daily_wins,
            "daily_losses": self.daily_losses,
            "win_rate": self.daily_wins / max(self.daily_trades, 1),
            "win_streak": self.win_streak,
            "loss_streak": self.loss_streak,
            "current_drawdown": self.current_drawdown,
        }


risk_manager = RiskManager()
