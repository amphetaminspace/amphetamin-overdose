"""
Machine Learning & Adaptive Learning Module.
Learns from wins and mistakes to continuously improve.
Uses reinforcement learning concepts and pattern recognition.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
from loguru import logger

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import joblib


@dataclass
class TradeOutcome:
    """Structured trade outcome for learning."""
    trade_id: int
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    indicators_at_entry: Dict
    market_regime: str
    strategy: str
    was_winner: bool
    duration_minutes: float


@dataclass
class LearningInsight:
    """Generated insight from pattern analysis."""
    category: str  # strategy, timing, risk, market_regime
    insight: str
    confidence: float
    actionable: bool
    suggested_change: str


class AdaptiveLearner:
    """
    Learns from trading history to:
    1. Identify which strategies work best in which conditions
    2. Detect patterns in winning vs losing trades
    3. Optimize entry/exit timing
    4. Adapt to changing market regimes
    5. Improve signal confidence calibration
    """

    def __init__(self):
        self.strategy_performance: Dict[str, Dict] = defaultdict(lambda: {
            "wins": 0, "losses": 0, "total_pnl": 0.0, "trades": 0
        })
        self.regime_performance: Dict[str, Dict] = defaultdict(lambda: {
            "wins": 0, "losses": 0, "total_pnl": 0.0, "trades": 0
        })
        self.indicator_patterns: Dict[str, List] = defaultdict(list)
        self.trade_outcomes: List[TradeOutcome] = []
        self.insights: List[LearningInsight] = []
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.min_training_samples = 50

    def record_trade(self, outcome: TradeOutcome):
        """Record a completed trade for learning."""
        self.trade_outcomes.append(outcome)

        # Update strategy performance
        strat = self.strategy_performance[outcome.strategy]
        strat["trades"] += 1
        strat["total_pnl"] += outcome.pnl_pct
        if outcome.was_winner:
            strat["wins"] += 1
        else:
            strat["losses"] += 1

        # Update regime performance
        regime = self.regime_performance[outcome.market_regime]
        regime["trades"] += 1
        regime["total_pnl"] += outcome.pnl_pct
        if outcome.was_winner:
            regime["wins"] += 1
        else:
            regime["losses"] += 1

        # Store indicator patterns
        for indicator, value in outcome.indicators_at_entry.items():
            if isinstance(value, (int, float)):
                self.indicator_patterns[indicator].append({
                    "value": value,
                    "was_winner": outcome.was_winner,
                })

    def train_model(self) -> bool:
        """
        Train ML model on trade outcomes to predict win probability.
        """
        if len(self.trade_outcomes) < self.min_training_samples:
            logger.info(f"Not enough data to train. Need {self.min_training_samples}, have {len(self.trade_outcomes)}")
            return False

        try:
            # Prepare features
            features = []
            labels = []

            for outcome in self.trade_outcomes[-500:]:  # Last 500 trades
                feat = self._extract_features(outcome.indicators_at_entry)
                if feat is not None:
                    features.append(feat)
                    labels.append(1 if outcome.was_winner else 0)

            if len(features) < self.min_training_samples:
                return False

            X = np.array(features)
            y = np.array(labels)

            # Scale features
            X_scaled = self.scaler.fit_transform(X)

            # Train ensemble model
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42,
            )
            self.model.fit(X_scaled, y)

            # Cross-validation score
            scores = cross_val_score(self.model, X_scaled, y, cv=5, scoring="accuracy")
            accuracy = scores.mean()
            self.is_trained = True

            logger.info(f"Learning model trained. CV Accuracy: {accuracy:.2%}")
            return True

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False

    def predict_win_probability(self, indicators: Dict) -> float:
        """Predict probability of a trade being a winner."""
        if not self.is_trained or self.model is None:
            return 0.5  # Neutral if model not trained

        try:
            features = self._extract_features(indicators)
            if features is None:
                return 0.5

            X = np.array([features])
            X_scaled = self.scaler.transform(X)
            prob = self.model.predict_proba(X_scaled)[0][1]
            return prob
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return 0.5

    def _extract_features(self, indicators: Dict) -> Optional[np.ndarray]:
        """Extract numerical features from indicator dict."""
        feature_names = [
            "rsi", "macd", "macd_histogram", "adx", "atr",
            "ema_9", "ema_21", "ema_50",
            "bb_width", "obv", "vwap", "mfi",
            "stochastic_k", "stochastic_d", "cci",
            "composite_score",
        ]

        features = []
        for name in feature_names:
            val = indicators.get(name, None)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                features.append(0.0)
            else:
                try:
                    features.append(float(val))
                except (ValueError, TypeError):
                    features.append(0.0)

        return np.array(features) if features else None

    def generate_insights(self) -> List[LearningInsight]:
        """
        Analyze patterns and generate actionable insights.
        """
        insights = []

        # 1. Strategy Performance Analysis
        for strategy, perf in self.strategy_performance.items():
            if perf["trades"] >= 10:
                win_rate = perf["wins"] / perf["trades"]
                avg_pnl = perf["total_pnl"] / perf["trades"]

                if win_rate > 0.6 and avg_pnl > 0:
                    insights.append(LearningInsight(
                        category="strategy",
                        insight=f"{strategy} is performing well: {win_rate:.0%} win rate, avg {avg_pnl:+.2f}%",
                        confidence=win_rate,
                        actionable=True,
                        suggested_change=f"Increase allocation to {strategy}",
                    ))
                elif win_rate < 0.4 and avg_pnl < 0:
                    insights.append(LearningInsight(
                        category="strategy",
                        insight=f"{strategy} is underperforming: {win_rate:.0%} win rate, avg {avg_pnl:+.2f}%",
                        confidence=1 - win_rate,
                        actionable=True,
                        suggested_change=f"Reduce or disable {strategy}",
                    ))

        # 2. Market Regime Analysis
        for regime, perf in self.regime_performance.items():
            if perf["trades"] >= 10:
                win_rate = perf["wins"] / perf["trades"]
                avg_pnl = perf["total_pnl"] / perf["trades"]

                if win_rate > 0.55:
                    insights.append(LearningInsight(
                        category="market_regime",
                        insight=f"Performing well in {regime} markets: {win_rate:.0%} win rate",
                        confidence=win_rate,
                        actionable=True,
                        suggested_change=f"Be more aggressive in {regime} conditions",
                    ))
                elif win_rate < 0.4:
                    insights.append(LearningInsight(
                        category="market_regime",
                        insight=f"Struggling in {regime} markets: {win_rate:.0%} win rate",
                        confidence=0.7,
                        actionable=True,
                        suggested_change=f"Be more conservative or avoid trading in {regime} markets",
                    ))

        # 3. Indicator Pattern Analysis
        for indicator, patterns in self.indicator_patterns.items():
            if len(patterns) >= 20:
                winner_vals = [p["value"] for p in patterns if p["was_winner"]]
                loser_vals = [p["value"] for p in patterns if not p["was_winner"]]

                if winner_vals and loser_vals:
                    win_mean = np.mean(winner_vals)
                    lose_mean = np.mean(loser_vals)
                    win_std = np.std(winner_vals)

                    # Check if there's a significant difference
                    if win_std > 0 and abs(win_mean - lose_mean) > win_std * 0.5:
                        if win_mean > lose_mean:
                            insights.append(LearningInsight(
                                category="indicator",
                                insight=f"Winning trades tend to have higher {indicator} (avg: {win_mean:.2f} vs {lose_mean:.2f})",
                                confidence=0.7,
                                actionable=True,
                                suggested_change=f"Require higher {indicator} for entries",
                            ))
                        else:
                            insights.append(LearningInsight(
                                category="indicator",
                                insight=f"Winning trades tend to have lower {indicator} (avg: {win_mean:.2f} vs {lose_mean:.2f})",
                                confidence=0.7,
                                actionable=True,
                                suggested_change=f"Require lower {indicator} for entries",
                            ))

        # 4. Timing Analysis
        if len(self.trade_outcomes) >= 20:
            # Analyze if certain durations are more profitable
            durations = [o.duration_minutes for o in self.trade_outcomes if o.duration_minutes > 0]
            if durations:
                short_trades = [o for o in self.trade_outcomes if 0 < o.duration_minutes <= 5]
                long_trades = [o for o in self.trade_outcomes if o.duration_minutes > 15]

                if short_trades and long_trades:
                    short_wr = sum(1 for o in short_trades if o.was_winner) / len(short_trades)
                    long_wr = sum(1 for o in long_trades if o.was_winner) / len(long_trades)

                    if short_wr > long_wr + 0.1:
                        insights.append(LearningInsight(
                            category="timing",
                            insight=f"Short trades (≤5min) outperform: {short_wr:.0%} vs {long_wr:.0%}",
                            confidence=0.6,
                            actionable=True,
                            suggested_change="Take profits faster, reduce hold times",
                        ))

        self.insights = insights
        return insights

    def get_optimal_parameters(self) -> Dict:
        """
        Suggest optimal trading parameters based on learning.
        """
        params = {
            "confidence_threshold": 0.55,
            "position_size_multiplier": 1.0,
            "leverage_cap": 25.0,
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 3.0,
            "preferred_strategies": [],
            "avoid_regimes": [],
        }

        # Adjust based on strategy performance
        best_strategy = None
        best_score = -999
        for strategy, perf in self.strategy_performance.items():
            if perf["trades"] >= 10:
                score = (perf["wins"] / perf["trades"]) * (perf["total_pnl"] / perf["trades"])
                if score > best_score:
                    best_score = score
                    best_strategy = strategy
                if perf["wins"] / perf["trades"] > 0.55:
                    params["preferred_strategies"].append(strategy)

        if best_strategy:
            params["primary_strategy"] = best_strategy

        # Adjust for regimes
        for regime, perf in self.regime_performance.items():
            if perf["trades"] >= 10:
                wr = perf["wins"] / perf["trades"]
                if wr < 0.4:
                    params["avoid_regimes"].append(regime)

        # Calibrate confidence threshold
        if self.trade_outcomes:
            winners = [o for o in self.trade_outcomes if o.was_winner]
            losers = [o for o in self.trade_outcomes if not o.was_winner]

            if winners and losers:
                # Find the composite score that best separates winners from losers
                win_scores = [o.indicators_at_entry.get("composite_score", 0) for o in winners]
                lose_scores = [o.indicators_at_entry.get("composite_score", 0) for o in losers]

                if win_scores and lose_scores:
                    # Optimal threshold is where win distribution starts
                    threshold = np.percentile(lose_scores, 75)
                    params["min_composite_score"] = max(10, threshold)

        return params

    def get_strategy_weights(self) -> Dict[str, float]:
        """
        Calculate dynamic weights for each strategy based on performance.
        Higher weight = more trades from this strategy.
        """
        weights = {}
        total_score = 0

        for strategy, perf in self.strategy_performance.items():
            if perf["trades"] >= 5:
                win_rate = perf["wins"] / perf["trades"]
                avg_pnl = perf["total_pnl"] / perf["trades"]
                # Score combines win rate and profitability
                score = max(0, win_rate * avg_pnl)
                weights[strategy] = score
                total_score += score

        # Normalize
        if total_score > 0:
            weights = {k: v / total_score for k, v in weights.items()}
        else:
            # Equal weights if no data
            n = len(weights)
            weights = {k: 1 / n for k in weights} if n > 0 else {"EMA_Crossover": 1.0}

        return weights

    def save_model(self, path: str = "models/learner.pkl"):
        """Save trained model."""
        if self.is_trained and self.model is not None:
            joblib.dump({"model": self.model, "scaler": self.scaler}, path)
            logger.info(f"Model saved to {path}")

    def load_model(self, path: str = "models/learner.pkl") -> bool:
        """Load trained model."""
        try:
            data = joblib.load(path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.is_trained = True
            logger.info(f"Model loaded from {path}")
            return True
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            return False

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary."""
        total_trades = len(self.trade_outcomes)
        if total_trades == 0:
            return {"total_trades": 0}

        winners = sum(1 for o in self.trade_outcomes if o.was_winner)
        losers = total_trades - winners
        total_pnl = sum(o.pnl_pct for o in self.trade_outcomes)

        return {
            "total_trades": total_trades,
            "winners": winners,
            "losers": losers,
            "win_rate": winners / total_trades,
            "total_pnl_pct": total_pnl,
            "avg_pnl_pct": total_pnl / total_trades,
            "avg_win_pct": np.mean([o.pnl_pct for o in self.trade_outcomes if o.was_winner]) if winners > 0 else 0,
            "avg_loss_pct": np.mean([o.pnl_pct for o in self.trade_outcomes if not o.was_winner]) if losers > 0 else 0,
            "profit_factor": abs(sum(o.pnl_pct for o in self.trade_outcomes if o.was_winner) /
                                sum(o.pnl_pct for o in self.trade_outcomes if not o.was_winner)) if losers > 0 else float("inf"),
            "best_strategy": max(self.strategy_performance, key=lambda k: self.strategy_performance[k]["total_pnl"])
                if self.strategy_performance else "N/A",
            "worst_regime": min(self.regime_performance, key=lambda k: self.regime_performance[k]["total_pnl"])
                if self.regime_performance else "N/A",
            "model_trained": self.is_trained,
            "num_insights": len(self.insights),
        }


learner = AdaptiveLearner()
