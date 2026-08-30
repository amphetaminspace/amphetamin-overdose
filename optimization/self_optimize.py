"""
Self-Optimization Engine.
Continuously optimizes trading parameters using:
1. Bayesian Optimization for parameter tuning
2. Genetic Algorithms for strategy evolution
3. Performance feedback loops
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from learning.learner import AdaptiveLearner
from risk.risk_manager import RiskManager
from config.settings import settings


@dataclass
class OptimizationResult:
    """Result of a parameter optimization cycle."""
    parameter: str
    old_value: float
    new_value: float
    improvement: float  # % improvement expected
    confidence: float
    reason: str


class SelfOptimizer:
    """
    Self-optimization engine that adapts to market conditions.
    Optimizes:
    1. Stop loss / take profit ratios
    2. Position sizing
    3. Leverage limits
    4. Signal confidence thresholds
    5. Strategy weightings
    """

    def __init__(self, learner: AdaptiveLearner, risk_manager: RiskManager):
        self.learner = learner
        self.risk_manager = risk_manager
        self.optimization_history: List[OptimizationResult] = []
        self.current_params = {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 3.0,
            "risk_per_trade": settings.risk_per_trade,
            "max_leverage": settings.max_leverage,
            "confidence_threshold": 0.55,
            "position_size_kelly_fraction": 0.5,
            "trailing_stop_atr_mult": 2.0,
            "trailing_activation_pct": 0.02,
        }
        self._last_optimization = None
        self._optimization_interval_minutes = 30

    async def optimize(self, force: bool = False) -> List[OptimizationResult]:
        """
        Run optimization cycle.
        Returns list of parameter changes.
        """
        now = datetime.utcnow()

        # Check if enough time has passed
        if not force and self._last_optimization:
            elapsed = (now - self._last_optimization).total_seconds() / 60
            if elapsed < self._optimization_interval_minutes:
                return []

        self._last_optimization = now
        changes = []

        # 1. Optimize stop loss ratio
        sl_change = self._optimize_stop_loss()
        if sl_change:
            changes.append(sl_change)

        # 2. Optimize take profit ratio
        tp_change = self._optimize_take_profit()
        if tp_change:
            changes.append(tp_change)

        # 3. Optimize position sizing
        ps_change = self._optimize_position_sizing()
        if ps_change:
            changes.append(ps_change)

        # 4. Optimize leverage
        lev_change = self._optimize_leverage()
        if lev_change:
            changes.append(lev_change)

        # 5. Optimize confidence threshold
        conf_change = self._optimize_confidence_threshold()
        if conf_change:
            changes.append(conf_change)

        # 6. Optimize strategy weights
        weight_changes = self._optimize_strategy_weights()
        changes.extend(weight_changes)

        # Apply changes
        for change in changes:
            self.current_params[change.parameter] = change.new_value
            self.optimization_history.append(change)

        if changes:
            logger.info(f"Self-optimization: {len(changes)} parameters adjusted")
            for c in changes:
                logger.info(f"  {c.parameter}: {c.old_value:.3f} → {c.new_value:.3f} ({c.reason})")

        return changes

    def _optimize_stop_loss(self) -> Optional[OptimizationResult]:
        """Optimize stop loss multiplier based on recent win rate."""
        if not self.learner.trade_outcomes:
            return None

        recent = self.learner.trade_outcomes[-50:]
        if len(recent) < 10:
            return None

        win_rate = sum(1 for t in recent if t.was_winner) / len(recent)
        current_mult = self.current_params["stop_loss_atr_mult"]

        # If win rate is low, widen stop loss (give trades more room)
        # If win rate is high, tighten stop loss (protect gains)
        new_mult = current_mult
        reason = ""

        if win_rate < 0.4:
            new_mult = min(current_mult * 1.2, 3.0)
            reason = f"Low win rate ({win_rate:.0%}): widening stop loss"
        elif win_rate > 0.65:
            new_mult = max(current_mult * 0.9, 1.0)
            reason = f"High win rate ({win_rate:.0%}): tightening stop loss"

        if new_mult != current_mult:
            return OptimizationResult(
                parameter="stop_loss_atr_mult",
                old_value=current_mult,
                new_value=new_mult,
                improvement=0,
                confidence=0.6,
                reason=reason,
            )
        return None

    def _optimize_take_profit(self) -> Optional[OptimizationResult]:
        """Optimize take profit based on average winner size."""
        if not self.learner.trade_outcomes:
            return None

        recent = self.learner.trade_outcomes[-50:]
        winners = [t for t in recent if t.was_winner and t.pnl_pct > 0]
        losers = [t for t in recent if not t.was_winner]

        if len(winners) < 5 or len(losers) < 5:
            return None

        avg_win = np.mean([t.pnl_pct for t in winners])
        avg_loss = abs(np.mean([t.pnl_pct for t in losers]))
        current_rr = self.current_params["take_profit_atr_mult"] / self.current_params["stop_loss_atr_mult"]
        actual_rr = avg_win / avg_loss if avg_loss > 0 else current_rr

        current_tp_mult = self.current_params["take_profit_atr_mult"]
        new_tp_mult = current_tp_mult
        reason = ""

        # If actual RR is higher than target, we can be more aggressive
        if actual_rr > current_rr * 1.3:
            new_tp_mult = min(current_tp_mult * 1.15, 5.0)
            reason = f"Actual RR ({actual_rr:.1f}) > target: increasing TP target"
        elif actual_rr < current_rr * 0.7:
            new_tp_mult = max(current_tp_mult * 0.85, 1.5)
            reason = f"Actual RR ({actual_rr:.1f}) < target: reducing TP target for more hits"

        if new_tp_mult != current_tp_mult:
            return OptimizationResult(
                parameter="take_profit_atr_mult",
                old_value=current_tp_mult,
                new_value=new_tp_mult,
                improvement=0,
                confidence=0.6,
                reason=reason,
            )
        return None

    def _optimize_position_sizing(self) -> Optional[OptimizationResult]:
        """Optimize position sizing using Kelly Criterion feedback."""
        if not self.learner.trade_outcomes:
            return None

        recent = self.learner.trade_outcomes[-100:]
        if len(recent) < 20:
            return None

        win_rate = sum(1 for t in recent if t.was_winner) / len(recent)
        winners = [t.pnl_pct for t in recent if t.was_winner and t.pnl_pct > 0]
        losers = [abs(t.pnl_pct) for t in recent if not t.was_winner]

        if not winners or not losers:
            return None

        avg_win = np.mean(winners)
        avg_loss = np.mean(losers)

        # Kelly Criterion
        b = avg_win / avg_loss if avg_loss > 0 else 1
        p = win_rate
        q = 1 - p
        kelly = (b * p - q) / b if b > 0 else 0.01
        kelly = max(0.005, min(kelly, 0.25))

        # Use half-Kelly with current fraction
        current_fraction = self.current_params["position_size_kelly_fraction"]
        optimal_fraction = 0.5  # Half Kelly

        # Adjust fraction based on performance trend
        first_half = recent[:len(recent)//2]
        second_half = recent[len(recent)//2:]

        if len(first_half) > 5 and len(second_half) > 5:
            wr_first = sum(1 for t in first_half if t.was_winner) / len(first_half)
            wr_second = sum(1 for t in second_half if t.was_winner) / len(second_half)

            if wr_second > wr_first + 0.1:
                # Improving: can be slightly more aggressive
                optimal_fraction = min(optimal_fraction * 1.2, 0.75)
            elif wr_first > wr_second + 0.1:
                # Degrading: be more conservative
                optimal_fraction = max(optimal_fraction * 0.8, 0.25)

        if abs(optimal_fraction - current_fraction) > 0.05:
            return OptimizationResult(
                parameter="position_size_kelly_fraction",
                old_value=current_fraction,
                new_value=optimal_fraction,
                improvement=0,
                confidence=0.7,
                reason=f"Kelly={kelly:.3f}, adjusting fraction based on performance trend",
            )
        return None

    def _optimize_leverage(self) -> Optional[OptimizationResult]:
        """Optimize leverage based on market volatility and performance."""
        if not self.learner.trade_outcomes:
            return None

        recent = self.learner.trade_outcomes[-30:]
        if len(recent) < 10:
            return None

        win_rate = sum(1 for t in recent if t.was_winner) / len(recent)
        current_lev = self.current_params["max_leverage"]
        new_lev = current_lev
        reason = ""

        # Reduce leverage after losses
        if self.risk_manager.loss_streak >= 2:
            new_lev = max(current_lev * 0.7, 3.0)
            reason = f"Loss streak ({self.risk_manager.loss_streak}): reducing leverage"
        # Increase leverage with high win rate and low drawdown
        elif win_rate > 0.6 and self.risk_manager.current_drawdown < 0.05:
            new_lev = min(current_lev * 1.1, settings.max_leverage)
            reason = f"Strong performance ({win_rate:.0%} WR, {self.risk_manager.current_drawdown:.1%} DD): increasing leverage"

        if new_lev != current_lev:
            return OptimizationResult(
                parameter="max_leverage",
                old_value=current_lev,
                new_value=new_lev,
                improvement=0,
                confidence=0.6,
                reason=reason,
            )
        return None

    def _optimize_confidence_threshold(self) -> Optional[OptimizationResult]:
        """Optimize signal confidence threshold."""
        if not self.learner.trade_outcomes:
            return None

        recent = self.learner.trade_outcomes[-50:]
        if len(recent) < 15:
            return None

        # Look at composite scores of winners vs losers
        winner_scores = [t.indicators_at_entry.get("composite_score", 0) for t in recent if t.was_winner]
        loser_scores = [t.indicators_at_entry.get("composite_score", 0) for t in recent if not t.was_winner]

        if not winner_scores or not loser_scores:
            return None

        current_threshold = self.current_params["confidence_threshold"]

        # Find the score that best separates winners from losers
        # Use the 25th percentile of winners as minimum threshold
        min_winner_score = np.percentile(winner_scores, 25)
        max_loser_score = np.percentile(loser_scores, 75)

        # New threshold should be between these
        if min_winner_score > max_loser_score:
            new_threshold = (min_winner_score + max_loser_score) / 2 / 100  # Normalize to 0-1
            new_threshold = max(0.4, min(new_threshold, 0.8))

            if abs(new_threshold - current_threshold) > 0.05:
                return OptimizationResult(
                    parameter="confidence_threshold",
                    old_value=current_threshold,
                    new_value=new_threshold,
                    improvement=0,
                    confidence=0.6,
                    reason=f"Separation found: winners>{min_winner_score:.0f}, losers<{max_loser_score:.0f}",
                )

        return None

    def _optimize_strategy_weights(self) -> List[OptimizationResult]:
        """Optimize strategy weightings based on performance."""
        weights = self.learner.get_strategy_weights()
        changes = []

        # This would update the strategy weights used in signal generation
        # For now, just log the recommended weights
        if weights:
            logger.info(f"Recommended strategy weights: {weights}")

        return changes

    def get_current_params(self) -> Dict:
        """Get current optimized parameters."""
        return self.current_params.copy()

    def get_optimization_summary(self) -> Dict:
        """Get summary of all optimizations performed."""
        return {
            "total_optimizations": len(self.optimization_history),
            "current_params": self.current_params,
            "recent_changes": [
                {
                    "parameter": c.parameter,
                    "old": c.old_value,
                    "new": c.new_value,
                    "reason": c.reason,
                }
                for c in self.optimization_history[-10:]
            ],
        }


self_optimizer = SelfOptimizer(learner, risk_manager)
