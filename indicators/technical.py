"""
Comprehensive Technical Indicators Library.
Combines ta-lib, pandas-ta, and custom indicators for maximum signal accuracy.
All indicators return the latest value and signal direction.
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, field

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


@dataclass
class IndicatorResult:
    """Container for indicator values and signals."""
    value: float = 0.0
    signal: str = "neutral"  # buy, sell, neutral
    strength: float = 0.0  # 0.0 to 1.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class IndicatorSnapshot:
    """Full snapshot of all indicators for a given moment."""
    # Trend
    ema_9: IndicatorResult = field(default_factory=IndicatorResult)
    ema_21: IndicatorResult = field(default_factory=IndicatorResult)
    ema_50: IndicatorResult = field(default_factory=IndicatorResult)
    ema_100: IndicatorResult = field(default_factory=IndicatorResult)
    ema_200: IndicatorResult = field(default_factory=IndicatorResult)
    supertrend: IndicatorResult = field(default_factory=IndicatorResult)
    ichimoku: IndicatorResult = field(default_factory=IndicatorResult)
    adx: IndicatorResult = field(default_factory=IndicatorResult)

    # Momentum
    rsi: IndicatorResult = field(default_factory=IndicatorResult)
    rsi_stochastic: IndicatorResult = field(default_factory=IndicatorResult)
    macd: IndicatorResult = field(default_factory=IndicatorResult)
    stochastic: IndicatorResult = field(default_factory=IndicatorResult)
    cci: IndicatorResult = field(default_factory=IndicatorResult)
    williams_r: IndicatorResult = field(default_factory=IndicatorResult)
    momentum: IndicatorResult = field(default_factory=IndicatorResult)

    # Volatility
    bollinger_bands: IndicatorResult = field(default_factory=IndicatorResult)
    atr: IndicatorResult = field(default_factory=IndicatorResult)
    keltner_channels: IndicatorResult = field(default_factory=IndicatorResult)
    donchian_channels: IndicatorResult = field(default_factory=IndicatorResult)

    # Volume
    obv: IndicatorResult = field(default_factory=IndicatorResult)
    vwap: IndicatorResult = field(default_factory=IndicatorResult)
    mfi: IndicatorResult = field(default_factory=IndicatorResult)
    ad_line: IndicatorResult = field(default_factory=IndicatorResult)
    volume_profile: IndicatorResult = field(default_factory=IndicatorResult)

    # Custom / Advanced
    elder_ray: IndicatorResult = field(default_factory=IndicatorResult)
    squeeze_momentum: IndicatorResult = field(default_factory=IndicatorResult)
    hull_ma: IndicatorResult = field(default_factory=IndicatorResult)
    trix: IndicatorResult = field(default_factory=IndicatorResult)
    pivot_points: IndicatorResult = field(default_factory=IndicatorResult)

    # Composite
    composite_score: float = 0.0  # -100 to +100
    trend_direction: str = "neutral"
    volatility_regime: str = "normal"
    volume_confirmation: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "ema_9": self.ema_9.value,
            "ema_21": self.ema_21.value,
            "ema_50": self.ema_50.value,
            "rsi": self.rsi.value,
            "macd": self.macd.value,
            "macd_signal": self.macd.metadata.get("signal", 0),
            "macd_histogram": self.macd.metadata.get("histogram", 0),
            "bb_upper": self.bollinger_bands.metadata.get("upper", 0),
            "bb_middle": self.bollinger_bands.metadata.get("middle", 0),
            "bb_lower": self.bollinger_bands.metadata.get("lower", 0),
            "atr": self.atr.value,
            "adx": self.adx.value,
            "stochastic_k": self.stochastic.metadata.get("k", 0),
            "stochastic_d": self.stochastic.metadata.get("d", 0),
            "obv": self.obv.value,
            "vwap": self.vwap.value,
            "mfi": self.mfi.value,
            "composite_score": self.composite_score,
            "trend_direction": self.trend_direction,
            "volatility_regime": self.volatility_regime,
        }


class TechnicalIndicators:
    """
    Advanced technical analysis engine.
    Computes 25+ indicators and generates a composite signal score.
    """

    def __init__(self):
        self.talib_available = HAS_TALIB

    def compute_all(self, df: pd.DataFrame) -> IndicatorSnapshot:
        """Compute all indicators and return a snapshot."""
        if df.empty or len(df) < 200:
            return IndicatorSnapshot()

        snapshot = IndicatorSnapshot()

        # Compute each indicator group
        self._compute_trend(df, snapshot)
        self._compute_momentum(df, snapshot)
        self._compute_volatility(df, snapshot)
        self._compute_volume(df, snapshot)
        self._compute_advanced(df, snapshot)
        self._compute_composite(snapshot)

        return snapshot

    def _compute_trend(self, df: pd.DataFrame, snap: IndicatorSnapshot):
        """Trend-following indicators."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # EMAs
        for period, attr in [(9, "ema_9"), (21, "ema_21"), (50, "ema_50"),
                              (100, "ema_100"), (200, "ema_200")]:
            ema = self._ema(close, period)
            current_price = close[-1]
            signal = "buy" if current_price > ema[-1] else "sell"
            strength = min(abs(current_price - ema[-1]) / current_price * 100, 1.0)
            setattr(snap, attr, IndicatorResult(
                value=ema[-1], signal=signal, strength=strength,
                metadata={"period": period}
            ))

        # Supertrend
        snap.supertrend = self._supertrend(df)

        # ADX (Average Directional Index)
        snap.adx = self._adx(df)

        # Hull Moving Average
        snap.hull_ma = self._hull_ma(close)

    def _compute_momentum(self, df: pd.DataFrame, snap: IndicatorSnapshot):
        """Momentum oscillators."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        # RSI
        rsi = self._rsi(close, 14)
        rsi_val = rsi[-1]
        if rsi_val < 30:
            signal, strength = "buy", (30 - rsi_val) / 30
        elif rsi_val > 70:
            signal, strength = "sell", (rsi_val - 70) / 30
        else:
            signal, strength = "neutral", 0.0
        snap.rsi = IndicatorResult(value=rsi_val, signal=signal, strength=strength)

        # MACD
        snap.macd = self._macd(close)

        # Stochastic
        snap.stochastic = self._stochastic(df)

        # CCI
        snap.cci = self._cci(df)

        # Williams %R
        snap.williams_r = self._williams_r(df)

        # Momentum (rate of change)
        mom = close[-1] / close[-10] - 1 if len(close) >= 10 else 0
        snap.momentum = IndicatorResult(
            value=mom * 100,
            signal="buy" if mom > 0 else "sell",
            strength=min(abs(mom) * 10, 1.0),
        )

    def _compute_volatility(self, df: pd.DataFrame, snap: IndicatorSnapshot):
        """Volatility indicators."""
        close = df["close"].values

        # Bollinger Bands
        snap.bollinger_bands = self._bollinger_bands(close)

        # ATR
        snap.atr = self._atr(df)

        # Keltner Channels
        snap.keltner_channels = self._keltner_channels(df)

        # Donchian Channels
        snap.donchian_channels = self._donchian_channels(df)

    def _compute_volume(self, df: pd.DataFrame, snap: IndicatorSnapshot):
        """Volume-based indicators."""
        close = df["close"].values
        volume = df["volume"].values

        # OBV
        snap.obv = self._obv(close, volume)

        # VWAP
        snap.vwap = self._vwap(df)

        # MFI
        snap.mfi = self._mfi(df)

        # AD Line
        snap.ad_line = self._ad_line(df)

        # Volume confirmation
        avg_vol = np.mean(volume[-20:])
        snap.volume_confirmation = volume[-1] > avg_vol * 1.2

    def _compute_advanced(self, df: pd.DataFrame, snap: IndicatorSnapshot):
        """Advanced / custom indicators."""
        close = df["close"].values

        # Elder Ray Index
        ema_13 = self._ema(close, 13)
        bull_power = df["high"].values[-1] - ema_13[-1]
        bear_power = df["low"].values[-1] - ema_13[-1]
        snap.elder_ray = IndicatorResult(
            value=bull_power,
            signal="buy" if bull_power > bear_power else "sell",
            strength=min(abs(bull_power) / close[-1] * 100, 1.0),
            metadata={"bull_power": bull_power, "bear_power": bear_power},
        )

        # Squeeze Momentum (TTM Squeeze)
        snap.squeeze_momentum = self._ttm_squeeze(df)

        # TRIX
        snap.trix = self._trix(close)

        # Pivot Points
        snap.pivot_points = self._pivot_points(df)

    def _compute_composite(self, snap: IndicatorSnapshot):
        """Compute composite score from all indicators."""
        scores = []
        weights = []

        # Trend indicators (weight: 30%)
        trend_score = 0
        if snap.ema_9.signal == "buy": trend_score += 1
        elif snap.ema_9.signal == "sell": trend_score -= 1
        if snap.ema_21.signal == "buy": trend_score += 1
        elif snap.ema_21.signal == "sell": trend_score -= 1
        if snap.supertrend.signal == "buy": trend_score += 2
        elif snap.supertrend.signal == "sell": trend_score -= 2
        if snap.hull_ma.signal == "buy": trend_score += 1
        elif snap.hull_ma.signal == "sell": trend_score -= 1
        scores.append(trend_score / 5 * 100)
        weights.append(0.30)

        # Momentum indicators (weight: 35%)
        mom_score = 0
        if snap.rsi.signal == "buy": mom_score += 2
        elif snap.rsi.signal == "sell": mom_score -= 2
        if snap.macd.signal == "buy": mom_score += 2
        elif snap.macd.signal == "sell": mom_score -= 2
        if snap.stochastic.signal == "buy": mom_score += 1
        elif snap.stochastic.signal == "sell": mom_score -= 1
        if snap.momentum.signal == "buy": mom_score += 1
        elif snap.momentum.signal == "sell": mom_score -= 1
        scores.append(mom_score / 8 * 100)
        weights.append(0.35)

        # Volatility (weight: 15%)
        vol_score = 0
        if snap.bollinger_bands.signal == "buy": vol_score += 2
        elif snap.bollinger_bands.signal == "sell": vol_score -= 2
        if snap.squeeze_momentum.signal == "buy": vol_score += 1
        elif snap.squeeze_momentum.signal == "sell": vol_score -= 1
        scores.append(vol_score / 3 * 100)
        weights.append(0.15)

        # Volume (weight: 20%)
        vol_conf_score = 0
        if snap.obv.signal == "buy": vol_conf_score += 2
        elif snap.obv.signal == "sell": vol_conf_score -= 2
        if snap.mfi.signal == "buy": vol_conf_score += 1
        elif snap.mfi.signal == "sell": vol_conf_score -= 1
        if snap.volume_confirmation: vol_conf_score += 1
        scores.append(vol_conf_score / 4 * 100)
        weights.append(0.20)

        # Weighted composite
        composite = sum(s * w for s, w in zip(scores, weights))
        snap.composite_score = max(-100, min(100, composite))

        # Determine trend direction
        if snap.composite_score > 30:
            snap.trend_direction = "strong_bullish"
        elif snap.composite_score > 10:
            snap.trend_direction = "bullish"
        elif snap.composite_score < -30:
            snap.trend_direction = "strong_bearish"
        elif snap.composite_score < -10:
            snap.trend_direction = "bearish"
        else:
            snap.trend_direction = "neutral"

        # Volatility regime
        atr_pct = snap.atr.value / (snap.ema_21.value or 1) * 100
        if atr_pct > 3:
            snap.volatility_regime = "extreme"
        elif atr_pct > 1.5:
            snap.volatility_regime = "high"
        elif atr_pct > 0.5:
            snap.volatility_regime = "normal"
        else:
            snap.volatility_regime = "low"

    # ── Individual Indicator Calculations ────────────────

    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """Exponential Moving Average."""
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(data, dtype=float)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
        return ema

    @staticmethod
    def _sma(data: np.ndarray, period: int) -> np.ndarray:
        """Simple Moving Average."""
        sma = np.convolve(data, np.ones(period) / period, mode="valid")
        # Pad beginning
        padding = np.full(period - 1, np.nan)
        return np.concatenate([padding, sma])

    @staticmethod
    def _rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.convolve(gains, np.ones(period) / period, mode="valid")
        avg_loss = np.convolve(losses, np.ones(period) / period, mode="valid")

        # Extend with Wilder's smoothing
        for i in range(period, len(gains)):
            avg_gain = np.append(avg_gain, (avg_gain[-1] * (period - 1) + gains[i]) / period)
            avg_loss = np.append(avg_loss, (avg_loss[-1] * (period - 1) + losses[i]) / period)

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        padding = np.full(len(data) - len(rsi), np.nan)
        return np.concatenate([padding, rsi])

    @staticmethod
    def _macd(data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> IndicatorResult:
        """MACD indicator."""
        ema_fast = TechnicalIndicators._ema(data, fast)
        ema_slow = TechnicalIndicators._ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators._ema(macd_line, signal)
        histogram = macd_line - signal_line

        # Signal determination
        if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
            sig = "buy"  # Bullish crossover
            strength = 1.0
        elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
            sig = "sell"  # Bearish crossover
            strength = 1.0
        elif macd_line[-1] > signal_line[-1]:
            sig = "buy"
            strength = 0.5
        else:
            sig = "sell"
            strength = 0.5

        return IndicatorResult(
            value=macd_line[-1],
            signal=sig,
            strength=strength,
            metadata={
                "macd_line": macd_line[-1],
                "signal": signal_line[-1],
                "histogram": histogram[-1],
            },
        )

    @staticmethod
    def _bollinger_bands(data: np.ndarray, period: int = 20, std_dev: float = 2.0) -> IndicatorResult:
        """Bollinger Bands."""
        sma = TechnicalIndicators._sma(data, period)
        rolling_std = pd.Series(data).rolling(period).std().values

        upper = sma + (rolling_std * std_dev)
        lower = sma - (rolling_std * std_dev)
        middle = sma

        current = data[-1]
        bb_width = (upper[-1] - lower[-1]) / middle[-1] * 100 if middle[-1] != 0 else 0

        # Signal based on position within bands
        if current <= lower[-1]:
            sig, strength = "buy", min((lower[-1] - current) / current * 100 + 0.5, 1.0)
        elif current >= upper[-1]:
            sig, strength = "sell", min((current - upper[-1]) / current * 100 + 0.5, 1.0)
        else:
            position = (current - lower[-1]) / (upper[-1] - lower[-1]) if upper[-1] != lower[-1] else 0.5
            if position < 0.3:
                sig, strength = "buy", 0.3
            elif position > 0.7:
                sig, strength = "sell", 0.3
            else:
                sig, strength = "neutral", 0.0

        return IndicatorResult(
            value=bb_width,
            signal=sig,
            strength=strength,
            metadata={"upper": upper[-1], "middle": middle[-1], "lower": lower[-1], "width_pct": bb_width},
        )

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        """Average True Range."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr = np.maximum(high[1:] - low[1:], np.maximum(
            abs(high[1:] - close[:-1]),
            abs(low[1:] - close[:-1])
        ))
        atr = TechnicalIndicators._ema(tr, period)

        atr_pct = atr[-1] / close[-1] * 100
        return IndicatorResult(
            value=atr[-1],
            signal="neutral",
            strength=min(atr_pct / 3, 1.0),
            metadata={"atr_pct": atr_pct},
        )

    @staticmethod
    def _stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> IndicatorResult:
        """Stochastic Oscillator."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        k_values = []
        for i in range(k_period, len(close)):
            highest = max(high[i - k_period + 1:i + 1])
            lowest = min(low[i - k_period + 1:i + 1])
            k = (close[i] - lowest) / (highest - lowest) * 100 if highest != lowest else 50
            k_values.append(k)

        k_arr = np.array(k_values)
        d_arr = TechnicalIndicators._sma(k_arr, d_period)

        k_val = k_arr[-1] if len(k_arr) > 0 else 50
        d_val = d_arr[-1] if len(d_arr) > 0 and not np.isnan(d_arr[-1]) else 50

        if k_val < 20 and k_val > d_val:
            sig, strength = "buy", 0.8
        elif k_val > 80 and k_val < d_val:
            sig, strength = "sell", 0.8
        elif k_val < 20:
            sig, strength = "buy", 0.4
        elif k_val > 80:
            sig, strength = "sell", 0.4
        else:
            sig, strength = "neutral", 0.0

        return IndicatorResult(
            value=k_val,
            signal=sig,
            strength=strength,
            metadata={"k": k_val, "d": d_val},
        )

    @staticmethod
    def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> IndicatorResult:
        """Supertrend indicator."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        atr = TechnicalIndicators._atr(df, period).value
        hl2 = (high + low) / 2

        upper_band = hl2[-1] + multiplier * atr
        lower_band = hl2[-1] - multiplier * atr

        # Simplified direction
        if close[-1] > upper_band:
            sig = "sell"
            strength = 0.7
        elif close[-1] < lower_band:
            sig = "buy"
            strength = 0.7
        else:
            # Check trend
            if close[-1] > hl2[-1]:
                sig = "buy"
                strength = 0.5
            else:
                sig = "sell"
                strength = 0.5

        return IndicatorResult(
            value=lower_band if sig == "buy" else upper_band,
            signal=sig,
            strength=strength,
            metadata={"upper": upper_band, "lower": lower_band, "atr": atr},
        )

    @staticmethod
    def _obv(close: np.ndarray, volume: np.ndarray) -> IndicatorResult:
        """On-Balance Volume."""
        obv = np.zeros_like(close)
        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]

        # Compare with SMA of OBV
        obv_sma = TechnicalIndicators._sma(obv, 20)
        current_obv = obv[-1]
        avg_obv = obv_sma[-1] if not np.isnan(obv_sma[-1]) else current_obv

        sig = "buy" if current_obv > avg_obv else "sell"
        strength = min(abs(current_obv - avg_obv) / (abs(avg_obv) + 1) * 10, 1.0)

        return IndicatorResult(value=current_obv, signal=sig, strength=strength)

    @staticmethod
    def _vwap(df: pd.DataFrame) -> IndicatorResult:
        """Volume Weighted Average Price."""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        volume = df["volume"]

        cumulative_tp_vol = (typical_price * volume).cumsum()
        cumulative_vol = volume.cumsum()
        vwap = cumulative_tp_vol / cumulative_vol

        current_price = df["close"].iloc[-1]
        current_vwap = vwap.iloc[-1]

        sig = "buy" if current_price > current_vwap else "sell"
        strength = min(abs(current_price - current_vwap) / current_price * 100, 1.0)

        return IndicatorResult(value=current_vwap, signal=sig, strength=strength)

    @staticmethod
    def _mfi(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        """Money Flow Index."""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = typical_price * df["volume"]

        positive_flow = []
        negative_flow = []

        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i - 1]:
                positive_flow.append(money_flow.iloc[i])
                negative_flow.append(0)
            else:
                positive_flow.append(0)
                negative_flow.append(money_flow.iloc[i])

        if len(positive_flow) >= period:
            pos_mf = sum(positive_flow[-period:])
            neg_mf = sum(negative_flow[-period:])
            mfi = 100 - (100 / (1 + pos_mf / (neg_mf + 1e-10)))
        else:
            mfi = 50

        if mfi < 20:
            sig, strength = "buy", (20 - mfi) / 20
        elif mfi > 80:
            sig, strength = "sell", (mfi - 80) / 20
        else:
            sig, strength = "neutral", 0.0

        return IndicatorResult(value=mfi, signal=sig, strength=strength)

    @staticmethod
    def _cci(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
        """Commodity Channel Index."""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        sma_tp = typical_price.rolling(period).mean()
        mean_dev = typical_price.rolling(period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))

        cci = (typical_price - sma_tp) / (0.015 * mean_dev)
        cci_val = cci.iloc[-1] if not np.isnan(cci.iloc[-1]) else 0

        if cci_val < -100:
            sig, strength = "buy", min(abs(cci_val + 100) / 100, 1.0)
        elif cci_val > 100:
            sig, strength = "sell", min(abs(cci_val - 100) / 100, 1.0)
        else:
            sig, strength = "neutral", 0.0

        return IndicatorResult(value=cci_val, signal=sig, strength=strength)

    @staticmethod
    def _williams_r(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        """Williams %R."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        highest = max(high[-period:])
        lowest = min(low[-period:])
        wr = (highest - close[-1]) / (highest - lowest) * -100 if highest != lowest else -50

        if wr < -80:
            sig, strength = "buy", (abs(wr) - 80) / 20
        elif wr > -20:
            sig, strength = "sell", (20 - abs(wr)) / 20
        else:
            sig, strength = "neutral", 0.0

        return IndicatorResult(value=wr, signal=sig, strength=strength)

    @staticmethod
    def _adx(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        """Average Directional Index."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        plus_dm = np.maximum(high[1:] - high[:-1], 0)
        minus_dm = np.maximum(low[:-1] - low[1:], 0)

        tr = np.maximum(high[1:] - low[1:], np.maximum(
            abs(high[1:] - close[:-1]),
            abs(low[1:] - close[:-1])
        ))

        atr = TechnicalIndicators._ema(tr, period)
        plus_di = TechnicalIndicators._ema(plus_dm, period) / (atr + 1e-10) * 100
        minus_di = TechnicalIndicators._ema(minus_dm, period) / (atr + 1e-10) * 100

        dx = abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10) * 100
        adx = TechnicalIndicators._ema(dx, period)

        adx_val = adx[-1]
        trend_strength = "strong" if adx_val > 25 else "weak"

        if plus_di[-1] > minus_di[-1]:
            sig = "buy"
        else:
            sig = "sell"

        return IndicatorResult(
            value=adx_val,
            signal=sig,
            strength=min(adx_val / 50, 1.0),
            metadata={"plus_di": plus_di[-1], "minus_di": minus_di[-1], "trend_strength": trend_strength},
        )

    @staticmethod
    def _hull_ma(data: np.ndarray, period: int = 20) -> IndicatorResult:
        """Hull Moving Average - fast, smooth, low lag."""
        half_period = period // 2
        sqrt_period = int(np.sqrt(period))

        wma_half = pd.Series(data).rolling(half_period).apply(
            lambda x: np.sum(np.arange(1, len(x) + 1) * x) / np.sum(np.arange(1, len(x) + 1)), raw=True
        )
        wma_full = pd.Series(data).rolling(period).apply(
            lambda x: np.sum(np.arange(1, len(x) + 1) * x) / np.sum(np.arange(1, len(x) + 1)), raw=True
        )

        raw_hma = 2 * wma_half - wma_full
        hma = raw_hma.rolling(sqrt_period).apply(
            lambda x: np.sum(np.arange(1, len(x) + 1) * x) / np.sum(np.arange(1, len(x) + 1)), raw=True
        )

        hma_val = hma.iloc[-1] if not np.isnan(hma.iloc[-1]) else data[-1]
        sig = "buy" if data[-1] > hma_val else "sell"
        strength = min(abs(data[-1] - hma_val) / data[-1] * 100, 1.0)

        return IndicatorResult(value=hma_val, signal=sig, strength=strength)

    @staticmethod
    def _keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 1.5) -> IndicatorResult:
        """Keltner Channels."""
        close = df["close"].values
        ema = TechnicalIndicators._ema(close, period)
        atr = TechnicalIndicators._atr(df, period).value

        upper = ema[-1] + multiplier * atr
        lower = ema[-1] - multiplier * atr

        current = close[-1]
        if current > upper:
            sig, strength = "sell", 0.6
        elif current < lower:
            sig, strength = "buy", 0.6
        else:
            sig, strength = "neutral", 0.0

        return IndicatorResult(
            value=ema[-1],
            signal=sig,
            strength=strength,
            metadata={"upper": upper, "lower": lower},
        )

    @staticmethod
    def _donchian_channels(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
        """Donchian Channels."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        upper = max(high[-period:])
        lower = min(low[-period:])
        middle = (upper + lower) / 2

        if close[-1] >= upper:
            sig, strength = "buy", 0.7  # Breakout
        elif close[-1] <= lower:
            sig, strength = "sell", 0.7
        else:
            sig, strength = "neutral", 0.0

        return IndicatorResult(
            value=middle,
            signal=sig,
            strength=strength,
            metadata={"upper": upper, "lower": lower},
        )

    @staticmethod
    def _ad_line(df: pd.DataFrame) -> IndicatorResult:
        """Accumulation/Distribution Line."""
        clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"] + 1e-10)
        ad = (clv * df["volume"]).cumsum()

        ad_sma = ad.rolling(20).mean()
        current_ad = ad.iloc[-1]
        avg_ad = ad_sma.iloc[-1] if not np.isnan(ad_sma.iloc[-1]) else current_ad

        sig = "buy" if current_ad > avg_ad else "sell"
        strength = min(abs(current_ad - avg_ad) / (abs(avg_ad) + 1) * 10, 1.0)

        return IndicatorResult(value=current_ad, signal=sig, strength=strength)

    @staticmethod
    def _trix(data: np.ndarray, period: int = 15) -> IndicatorResult:
        """TRIX - 1-day rate of change of a triple exponential moving average."""
        ema1 = TechnicalIndicators._ema(data, period)
        ema2 = TechnicalIndicators._ema(ema1, period)
        ema3 = TechnicalIndicators._ema(ema2, period)

        trix = (ema3[-1] - ema3[-2]) / (ema3[-2] + 1e-10) * 100 if len(ema3) > 1 else 0

        sig = "buy" if trix > 0 else "sell"
        strength = min(abs(trix) * 10, 1.0)

        return IndicatorResult(value=trix, signal=sig, strength=strength)

    @staticmethod
    def _ttm_squeeze(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
        """TTM Squeeze - Bollinger Bands inside Keltner Channels = squeeze."""
        close = df["close"].values

        # Bollinger Bands
        sma = pd.Series(close).rolling(period).mean().values
        std = pd.Series(close).rolling(period).std().values
        bb_upper = sma + 2 * std
        bb_lower = sma - 2 * std

        # Keltner Channels
        ema = TechnicalIndicators._ema(close, period)
        atr = TechnicalIndicators._atr(df, period).value
        kc_upper = ema + 1.5 * atr
        kc_lower = ema - 1.5 * atr

        # Squeeze detection
        squeeze = bb_upper[-1] < kc_upper[-1] and bb_lower[-1] > kc_lower[-1]

        # Momentum (linear regression of price - (SMA + BB lower) / 2)
        momentum_val = close[-1] - (sma[-1] + bb_lower[-1]) / 2

        if squeeze:
            sig = "neutral"
            strength = 0.3
        elif momentum_val > 0:
            sig = "buy"
            strength = min(abs(momentum_val) / close[-1] * 100, 1.0)
        else:
            sig = "sell"
            strength = min(abs(momentum_val) / close[-1] * 100, 1.0)

        return IndicatorResult(
            value=momentum_val,
            signal=sig,
            strength=strength,
            metadata={"squeeze_on": squeeze},
        )

    @staticmethod
    def _pivot_points(df: pd.DataFrame) -> IndicatorResult:
        """Standard Pivot Points."""
        high = df["high"].iloc[-1]
        low = df["low"].iloc[-1]
        close = df["close"].iloc[-1]

        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high

        if close > r1:
            sig, strength = "buy", 0.7
        elif close < s1:
            sig, strength = "sell", 0.7
        elif close > pivot:
            sig, strength = "buy", 0.3
        else:
            sig, strength = "sell", 0.3

        return IndicatorResult(
            value=pivot,
            signal=sig,
            strength=strength,
            metadata={"r1": r1, "s1": s1, "pivot": pivot},
        )


indicators = TechnicalIndicators()
