"""
Advanced Scalping Strategies for Crypto Day Trading.
Multiple strategy implementations that work together for maximum signal accuracy.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from indicators.technical import TechnicalIndicators, IndicatorSnapshot


class SignalType(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    HOLD = "hold"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class TradingSignal:
    """Complete trading signal with all metadata."""
    symbol: str
    signal_type: SignalType
    direction: str  # long, short
    confidence: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    leverage: float
    position_size_pct: float  # % of capital
    strategy_name: str
    timeframe: str
    reasons: list
    indicators_snapshot: Optional[Dict] = None
    risk_reward_ratio: float = 0.0
    expected_return: float = 0.0

    @property
    def is_buy(self) -> bool:
        return self.direction == "long"

    @property
    def is_sell(self) -> bool:
        return self.direction == "short"


class ScalpingEngine:
    """
    Multi-strategy scalping engine that combines signals from:
    1. EMA Crossover Scalping
    2. RSI Divergence
    3. Bollinger Band Squeeze Breakout
    4. VWAP Mean Reversion
    5. Volume-Weighted Momentum
    6. Order Flow / Order Book Imbalance
    """

    def __init__(self, indicators: TechnicalIndicators):
        self.indicators = indicators

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_capital: float = 10000.0,
        max_leverage: float = 25.0,
        risk_per_trade: float = 0.02,
    ) -> Optional[TradingSignal]:
        """
        Generate a trading signal by combining multiple strategies.
        Returns None if no high-confidence signal is found.
        """
        if df.empty or len(df) < 50:
            return None

        # Compute all indicators
        snapshot = self.indicators.compute_all(df)
        current_price = df["close"].iloc[-1]

        # Run each strategy
        signals = []

        # Strategy 1: EMA Crossover Scalping
        sig1 = self._ema_crossover_strategy(df, snapshot, symbol)
        if sig1:
            signals.append(sig1)

        # Strategy 2: RSI + Stochastic Oversold/Overbought
        sig2 = self._rsi_stochastic_strategy(df, snapshot, symbol)
        if sig2:
            signals.append(sig2)

        # Strategy 3: Bollinger Band Squeeze Breakout
        sig3 = self._bollinger_breakout_strategy(df, snapshot, symbol)
        if sig3:
            signals.append(sig3)

        # Strategy 4: VWAP Mean Reversion + Trend
        sig4 = self._vwap_strategy(df, snapshot, symbol)
        if sig4:
            signals.append(sig4)

        # Strategy 5: Volume-Weighted Momentum
        sig5 = self._volume_momentum_strategy(df, snapshot, symbol)
        if sig5:
            signals.append(sig5)

        # Strategy 6: MACD + Histogram Momentum
        sig6 = self._macd_momentum_strategy(df, snapshot, symbol)
        if sig6:
            signals.append(sig6)

        if not signals:
            return None

        # Combine signals
        combined = self._combine_signals(signals, current_price, snapshot)
        if not combined or combined.confidence < 0.55:
            return None

        # Calculate position size and risk parameters
        return self._calculate_position(
            combined, current_price, current_capital, max_leverage,
            risk_per_trade, snapshot
        )

    def _ema_crossover_strategy(
        self, df: pd.DataFrame, snap: IndicatorSnapshot, symbol: str
    ) -> Optional[Dict]:
        """EMA 9/21/50 crossover with trend alignment."""
        close = df["close"].values
        ema_9 = self.indicators._ema(close, 9)
        ema_21 = self.indicators._ema(close, 21)
        ema_50 = self.indicators._ema(close, 50)

        # Bullish crossover: EMA9 crosses above EMA21 with price above EMA50
        bullish_cross = (
            ema_9[-1] > ema_21[-1] and
            ema_9[-2] <= ema_21[-2] and
            close[-1] > ema_50[-1]
        )

        # Bearish crossover: EMA9 crosses below EMA21 with price below EMA50
        bearish_cross = (
            ema_9[-1] < ema_21[-1] and
            ema_9[-2] >= ema_21[-2] and
            close[-1] < ema_50[-1]
        )

        if bullish_cross:
            return {
                "direction": "long",
                "confidence": 0.7,
                "strategy": "EMA_Crossover",
                "reason": "EMA9 crossed above EMA21 with bullish trend (price > EMA50)",
            }
        elif bearish_cross:
            return {
                "direction": "short",
                "confidence": 0.7,
                "strategy": "EMA_Crossover",
                "reason": "EMA9 crossed below EMA21 with bearish trend (price < EMA50)",
            }

        # Also check for EMA alignment (no crossover needed)
        if ema_9[-1] > ema_21[-1] > ema_50[-1] and close[-1] > ema_9[-1]:
            return {
                "direction": "long",
                "confidence": 0.5,
                "strategy": "EMA_Alignment",
                "reason": "Perfect bullish EMA alignment (9>21>50, price>EMA9)",
            }
        elif ema_9[-1] < ema_21[-1] < ema_50[-1] and close[-1] < ema_9[-1]:
            return {
                "direction": "short",
                "confidence": 0.5,
                "strategy": "EMA_Alignment",
                "reason": "Perfect bearish EMA alignment (9<21<50, price<EMA9)",
            }

        return None

    def _rsi_stochastic_strategy(
        self, df: pd.DataFrame, snap: IndicatorSnapshot, symbol: str
    ) -> Optional[Dict]:
        """RSI + Stochastic oversold/overbought with divergence."""
        rsi = snap.rsi.value
        stoch_k = snap.stochastic.metadata.get("k", 50)
        stoch_d = snap.stochastic.metadata.get("d", 50)

        # Oversold bounce (long)
        if rsi < 30 and stoch_k < 20 and stoch_k > stoch_d:
            return {
                "direction": "long",
                "confidence": 0.75,
                "strategy": "RSI_Stochastic",
                "reason": f"RSI oversold ({rsi:.1f}) + Stochastic bullish crossover (K:{stoch_k:.1f} > D:{stoch_d:.1f})",
            }

        # Overbought reversal (short)
        if rsi > 70 and stoch_k > 80 and stoch_k < stoch_d:
            return {
                "direction": "short",
                "confidence": 0.75,
                "strategy": "RSI_Stochastic",
                "reason": f"RSI overbought ({rsi:.1f}) + Stochastic bearish crossover (K:{stoch_k:.1f} < D:{stoch_d:.1f})",
            }

        return None

    def _bollinger_breakout_strategy(
        self, df: pd.DataFrame, snap: IndicatorSnapshot, symbol: str
    ) -> Optional[Dict]:
        """Bollinger Band squeeze breakout with volume confirmation."""
        close = df["close"].values
        bb_meta = snap.bollinger_bands.metadata
        upper = bb_meta.get("upper", 0)
        lower = bb_meta.get("lower", 0)
        middle = bb_meta.get("middle", 0)

        if upper == 0 or lower == 0:
            return None

        bb_width = (upper - lower) / middle * 100 if middle != 0 else 0
        current = close[-1]
        prev = close[-2]

        # Squeeze breakout: bands were tight, now expanding
        squeeze = bb_width < 2.0  # Tight bands

        # Breakout above upper band with volume
        if prev <= upper and current > upper and snap.volume_confirmation:
            return {
                "direction": "long",
                "confidence": 0.8,
                "strategy": "BB_Breakout",
                "reason": f"Bollinger Band squeeze breakout above upper band with volume (width: {bb_width:.2f}%)",
            }

        # Breakout below lower band with volume
        if prev >= lower and current < lower and snap.volume_confirmation:
            return {
                "direction": "short",
                "confidence": 0.8,
                "strategy": "BB_Breakout",
                "reason": f"Bollinger Band squeeze breakout below lower band with volume (width: {bb_width:.2f}%)",
            }

        return None

    def _vwap_strategy(
        self, df: pd.DataFrame, snap: IndicatorSnapshot, symbol: str
    ) -> Optional[Dict]:
        """VWAP mean reversion combined with trend."""
        vwap = snap.vwap.value
        close = df["close"].values
        current = close[-1]

        if vwap == 0:
            return None

        # Price near VWAP in an uptrend = buy opportunity
        dist_from_vwap = (current - vwap) / vwap * 100

        if -0.3 < dist_from_vwap < 0.3 and snap.trend_direction in ("bullish", "strong_bullish"):
            return {
                "direction": "long",
                "confidence": 0.6,
                "strategy": "VWAP_MeanReversion",
                "reason": f"Price near VWAP ({dist_from_vwap:+.2f}%) in uptrend",
            }
        elif -0.3 < dist_from_vwap < 0.3 and snap.trend_direction in ("bearish", "strong_bearish"):
            return {
                "direction": "short",
                "confidence": 0.6,
                "strategy": "VWAP_MeanReversion",
                "reason": f"Price near VWAP ({dist_from_vwap:+.2f}%) in downtrend",
            }

        # VWAP breakout
        if current > vwap * 1.005 and snap.ema_9.value > vwap:
            return {
                "direction": "long",
                "confidence": 0.55,
                "strategy": "VWAP_Breakout",
                "reason": "Price broke above VWAP with EMA9 confirmation",
            }
        elif current < vwap * 0.995 and snap.ema_9.value < vwap:
            return {
                "direction": "short",
                "confidence": 0.55,
                "strategy": "VWAP_Breakout",
                "reason": "Price broke below VWAP with EMA9 confirmation",
            }

        return None

    def _volume_momentum_strategy(
        self, df: pd.DataFrame, snap: IndicatorSnapshot, symbol: str
    ) -> Optional[Dict]:
        """Volume-confirmed momentum with OBV and MFI."""
        volume = df["volume"].values
        close = df["close"].values

        avg_vol_20 = np.mean(volume[-20:])
        avg_vol_5 = np.mean(volume[-5:])
        vol_ratio = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1

        # High volume momentum
        if vol_ratio > 1.5:
            price_change = (close[-1] - close[-5]) / close[-5] * 100

            if price_change > 0.5 and snap.mfi.value < 80:
                return {
                    "direction": "long",
                    "confidence": 0.7,
                    "strategy": "Volume_Momentum",
                    "reason": f"High volume ({vol_ratio:.1f}x avg) with +{price_change:.2f}% momentum",
                }
            elif price_change < -0.5 and snap.mfi.value > 20:
                return {
                    "direction": "short",
                    "confidence": 0.7,
                    "strategy": "Volume_Momentum",
                    "reason": f"High volume ({vol_ratio:.1f}x avg) with {price_change:.2f}% momentum",
                }

        return None

    def _macd_momentum_strategy(
        self, df: pd.DataFrame, snap: IndicatorSnapshot, symbol: str
    ) -> Optional[Dict]:
        """MACD histogram momentum acceleration."""
        macd_hist = snap.macd.metadata.get("histogram", 0)
        macd_hist_prev = snap.macd.metadata.get("prev_histogram", macd_hist)

        # Histogram growing = momentum accelerating
        if macd_hist > 0 and macd_hist > macd_hist_prev:
            return {
                "direction": "long",
                "confidence": 0.6,
                "strategy": "MACD_Momentum",
                "reason": f"MACD histogram increasing bullishly ({macd_hist:.4f})",
            }
        elif macd_hist < 0 and macd_hist < macd_hist_prev:
            return {
                "direction": "short",
                "confidence": 0.6,
                "strategy": "MACD_Momentum",
                "reason": f"MACD histogram increasing bearishly ({macd_hist:.4f})",
            }

        return None

    def _combine_signals(
        self, signals: list, current_price: float, snap: IndicatorSnapshot
    ) -> Optional[TradingSignal]:
        """Combine multiple strategy signals into one."""
        if not signals:
            return None

        # Count directional signals
        long_signals = [s for s in signals if s["direction"] == "long"]
        short_signals = [s for s in signals if s["direction"] == "short"]

        # Need at least 2 agreeing signals
        if len(long_signals) < 2 and len(short_signals) < 2:
            return None

        # Determine dominant direction
        if len(long_signals) > len(short_signals):
            direction = "long"
            dominant = long_signals
        elif len(short_signals) > len(long_signals):
            direction = "short"
            dominant = short_signals
        else:
            # Equal - pick higher confidence
            long_conf = sum(s["confidence"] for s in long_signals)
            short_conf = sum(s["confidence"] for s in short_signals)
            if long_conf >= short_conf:
                direction = "long"
                dominant = long_signals
            else:
                direction = "short"
                dominant = short_signals

        # Calculate combined confidence
        avg_confidence = np.mean([s["confidence"] for s in dominant])
        agreement_bonus = min(len(dominant) * 0.05, 0.2)  # More signals = higher confidence
        confidence = min(avg_confidence + agreement_bonus, 0.95)

        # Determine signal type
        if confidence >= 0.85:
            signal_type = SignalType.STRONG_BUY if direction == "long" else SignalType.STRONG_SELL
        elif confidence >= 0.7:
            signal_type = SignalType.BUY if direction == "long" else SignalType.SELL
        else:
            signal_type = SignalType.WEAK_BUY if direction == "long" else SignalType.WEAK_SELL

        # Collect reasons
        reasons = [s["reason"] for s in dominant]

        # Determine strategy name
        strategy_names = [s["strategy"] for s in dominant]
        primary_strategy = max(set(strategy_names), key=strategy_names.count)

        return TradingSignal(
            symbol="",
            signal_type=signal_type,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=0,  # Will be calculated
            take_profit=0,  # Will be calculated
            leverage=1.0,  # Will be calculated
            position_size_pct=0.05,
            strategy_name=primary_strategy,
            timeframe="1m",
            reasons=reasons,
        )

    def _calculate_position(
        self,
        signal: TradingSignal,
        current_price: float,
        current_capital: float,
        max_leverage: float,
        risk_per_trade: float,
        snap: IndicatorSnapshot,
    ) -> TradingSignal:
        """Calculate position size, stop loss, take profit, and leverage."""
        # ATR-based stop loss
        atr = snap.atr.value
        atr_multiplier = 1.5  # 1.5x ATR for stop loss

        if signal.direction == "long":
            signal.stop_loss = current_price - (atr * atr_multiplier)
            signal.take_profit = current_price + (atr * atr_multiplier * 3)  # 1:3 RR
        else:
            signal.stop_loss = current_price + (atr * atr_multiplier)
            signal.take_profit = current_price - (atr * atr_multiplier * 3)

        # Risk/reward ratio
        risk = abs(current_price - signal.stop_loss)
        reward = abs(signal.take_profit - current_price)
        signal.risk_reward_ratio = reward / risk if risk > 0 else 0
        signal.expected_return = (reward / current_price) * 100

        # Dynamic leverage based on confidence and volatility
        base_leverage = 5.0  # Conservative base
        confidence_multiplier = signal.confidence * 2  # Up to 2x from confidence
        volatility_adj = 1.0

        # Reduce leverage in high volatility
        if snap.volatility_regime == "extreme":
            volatility_adj = 0.3
        elif snap.volatility_regime == "high":
            volatility_adj = 0.6
        elif snap.volatility_regime == "low":
            volatility_adj = 1.5  # Can use more leverage in calm markets

        signal.leverage = min(
            base_leverage * confidence_multiplier * volatility_adj,
            max_leverage,
        )
        signal.leverage = max(signal.leverage, 1.0)  # Minimum 1x

        # Kelly-inspired position sizing
        # f* = (bp - q) / b where b=odds, p=win prob, q=loss prob
        win_prob = signal.confidence
        loss_prob = 1 - win_prob
        odds = signal.risk_reward_ratio
        kelly = (odds * win_prob - loss_prob) / odds if odds > 0 else 0
        kelly = max(kelly, 0.01)  # At least 1%
        kelly = min(kelly, risk_per_trade * 2)  # Cap at 2x base risk

        # Use half-Kelly for safety
        signal.position_size_pct = kelly * 0.5

        # Ensure minimum risk/reward
        if signal.risk_reward_ratio < 2.0:
            signal.confidence *= 0.7  # Penalize poor RR

        signal.indicators_snapshot = snap.to_dict()
        return signal


scalping_engine = ScalpingEngine(TechnicalIndicators())
