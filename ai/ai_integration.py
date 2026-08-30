"""
AI Integration Module - LongCat & Gemini.
Provides market analysis, signal validation, and adaptive learning through LLMs.
"""
import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from config.settings import settings


@dataclass
class AIAnalysis:
    """Result from AI market analysis."""
    model: str
    decision: str  # buy, sell, hold
    confidence: float
    reasoning: str
    key_factors: List[str]
    risk_assessment: str
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None


class LongCatAI:
    """
    LongCat AI integration for market analysis and trading decisions.
    Uses LongCat's advanced reasoning for complex market analysis.
    """

    def __init__(self):
        self.api_key = settings.longcat_api_key
        self.model = "longcat-2.0"
        self._available = bool(self.api_key)

    async def analyze_market(
        self,
        symbol: str,
        indicators: dict,
        market_context: dict,
        recent_trades: List[dict] = None,
    ) -> Optional[AIAnalysis]:
        """
        Analyze market conditions using LongCat AI.
        """
        if not self._available:
            logger.warning("LongCat API key not configured")
            return None

        prompt = self._build_analysis_prompt(symbol, indicators, market_context, recent_trades)

        try:
            # In production, this would call the LongCat API
            # For now, we structure the prompt and return a placeholder
            # that would be replaced with actual API call
            response = await self._call_longcat(prompt)
            return self._parse_response("longcat", response)
        except Exception as e:
            logger.error(f"LongCat analysis failed for {symbol}: {e}")
            return None

    async def validate_trade_signal(
        self,
        symbol: str,
        signal: dict,
        indicators: dict,
    ) -> Optional[AIAnalysis]:
        """Validate a trading signal before execution."""
        if not self._available:
            return None

        prompt = f"""Validate this trading signal for {symbol}:

Signal: {signal.get('direction', 'unknown')} with {signal.get('confidence', 0):.0%} confidence
Strategy: {signal.get('strategy', 'unknown')}

Key Indicators:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A')}
- Composite Score: {indicators.get('composite_score', 'N/A')}/100
- Trend: {indicators.get('trend_direction', 'N/A')}
- Volatility: {indicators.get('volatility_regime', 'N/A')}

Should this trade be executed? Consider:
1. Risk/reward ratio
2. Market conditions
3. Signal quality
4. Current volatility regime

Respond with: APPROVE, REJECT, or REDUCE_SIZE and your reasoning."""

        try:
            response = await self._call_longcat(prompt)
            return self._parse_response("longcat", response)
        except Exception as e:
            logger.error(f"LongCat signal validation failed: {e}")
            return None

    async def generate_strategy_adaptation(
        self,
        recent_performance: Dict,
        market_regime: str,
    ) -> Optional[str]:
        """Generate strategy parameter adjustments based on recent performance."""
        if not self._available:
            return None

        prompt = f"""Based on recent trading performance and current market regime, suggest strategy adjustments:

Market Regime: {market_regime}
Recent Performance:
- Win Rate: {recent_performance.get('win_rate', 'N/A')}%
- Profit Factor: {recent_performance.get('profit_factor', 'N/A')}
- Avg Trade P&L: {recent_performance.get('avg_pnl', 'N/A')}%
- Sharpe Ratio: {recent_performance.get('sharpe', 'N/A')}
- Max Drawdown: {recent_performance.get('max_drawdown', 'N/A')}%

What parameters should be adjusted? Consider:
1. Position sizing
2. Stop loss / take profit ratios
3. Leverage limits
4. Signal confidence thresholds
5. Strategy weightings

Provide specific actionable recommendations."""

        try:
            response = await self._call_longcat(prompt)
            return response
        except Exception as e:
            logger.error(f"LongCat strategy adaptation failed: {e}")
            return None

    def _build_analysis_prompt(
        self,
        symbol: str,
        indicators: dict,
        market_context: dict,
        recent_trades: List[dict] = None,
    ) -> str:
        """Build comprehensive analysis prompt."""
        return f"""You are an expert crypto day trader and quantitative analyst.
Analyze the following market data for {symbol} and provide a trading decision.

Current Indicators:
{json.dumps(indicators, indent=2)}

Market Context:
- 24h Volume: {market_context.get('volume_24h', 'N/A')}
- 24h Change: {market_context.get('change_24h', 'N/A')}%
- Spread: {market_context.get('spread_pct', 'N/A')}%
- Volatility: {market_context.get('volatility_regime', 'N/A')}

Recent Trades: {len(recent_trades) if recent_trades else 0}

Provide your analysis in this exact format:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]%
REASONING: [your detailed analysis]
KEY_FACTORS: [list of 3-5 key factors]
RISK: [risk assessment]
PRICE_TARGET: [target price or N/A]
STOP_LOSS: [stop loss price or N/A]"""

    async def _call_longcat(self, prompt: str) -> str:
        """Call LongCat API - placeholder for actual implementation."""
        # In production, this would make an actual API call:
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(
        #         "https://api.longcat.ai/v1/chat/completions",
        #         headers={"Authorization": f"Bearer {self.api_key}"},
        #         json={"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        #     ) as resp:
        #         data = await resp.json()
        #         return data["choices"][0]["message"]["content"]
        logger.info(f"LongCat prompt prepared ({len(prompt)} chars)")
        return "HOLD\nCONFIDENCE: 50%\nReasoning: API integration pending"

    def _parse_response(self, model: str, response: str) -> AIAnalysis:
        """Parse AI response into structured format."""
        lines = response.strip().split("\n")
        decision = "hold"
        confidence = 0.5
        reasoning = ""
        key_factors = []
        risk = "medium"

        for line in lines:
            if line.startswith("DECISION:"):
                decision = line.split(":", 1)[1].strip().lower()
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf_str = line.split(":", 1)[1].strip().replace("%", "")
                    confidence = float(conf_str) / 100
                except (ValueError, IndexError):
                    confidence = 0.5
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
            elif line.startswith("KEY_FACTORS:"):
                key_factors = [f.strip() for f in line.split(":", 1)[1].split(",")]
            elif line.startswith("RISK:"):
                risk = line.split(":", 1)[1].strip()

        return AIAnalysis(
            model=model,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            key_factors=key_factors,
            risk_assessment=risk,
        )


class GeminiAI:
    """
    Google Gemini AI integration for market prediction and analysis.
    Specializes in pattern recognition and price prediction.
    """

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = "gemini-1.5-pro"
        self._available = bool(self.api_key)
        self._client = None

    async def initialize(self):
        """Initialize Gemini client."""
        if not self._available:
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
            logger.info("Gemini AI initialized")
        except ImportError:
            logger.warning("google-generativeai not installed")
            self._available = False
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")
            self._available = False

    async def predict_price_movement(
        self,
        symbol: str,
        ohlcv_data: List[Dict],
        indicators: dict,
    ) -> Optional[AIAnalysis]:
        """
        Predict short-term price movement using Gemini.
        """
        if not self._available or not self._client:
            return None

        # Format OHLCV data (last 20 candles)
        recent_candles = ohlcv_data[-20:] if len(ohlcv_data) > 20 else ohlcv_data
        candle_str = "\n".join(
            [f"O:{c['open']:.4f} H:{c['high']:.4f} L:{c['low']:.4f} C:{c['close']:.4f} V:{c['volume']:.2f}"
             for c in recent_candles]
        )

        prompt = f"""You are a professional crypto trading analyst with expertise in technical analysis.
Analyze the following data for {symbol} and predict the next 15-60 minute price movement.

Recent Candles (1-minute):
{candle_str}

Technical Indicators:
- RSI(14): {indicators.get('rsi', 'N/A')}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A')}
- EMA9: {indicators.get('ema_9', 'N/A')}
- EMA21: {indicators.get('ema_21', 'N/A')}
- ATR: {indicators.get('atr', 'N/A')}
- Bollinger Bands: Upper={indicators.get('bb_upper', 'N/A')}, Lower={indicators.get('bb_lower', 'N/A')}
- ADX: {indicators.get('adx', 'N/A')}
- Composite Score: {indicators.get('composite_score', 'N/A')}/100
- Trend: {indicators.get('trend_direction', 'N/A')}

Predict:
1. Direction (up/down/sideways)
2. Magnitude (percentage move expected)
3. Confidence level
4. Key support/resistance levels
5. Recommended action

Be concise and specific. Focus on actionable insights."""

        try:
            response = await asyncio.to_thread(
                self._client.generate_content, prompt
            )
            return self._parse_gemini_response(response.text)
        except Exception as e:
            logger.error(f"Gemini prediction failed for {symbol}: {e}")
            return None

    async def analyze_market_sentiment(
        self,
        symbol: str,
        order_book: Dict = None,
        recent_news: List[str] = None,
    ) -> Optional[str]:
        """Analyze market sentiment from multiple sources."""
        if not self._available or not self._client:
            return None

        prompt = f"""Analyze market sentiment for {symbol}.

Order Book Summary:
- Bid/Ask Ratio: {order_book.get('bid_ask_ratio', 'N/A') if order_book else 'N/A'}
- Spread: {order_book.get('spread', 'N/A') if order_book else 'N/A'}

Recent News: {recent_news[:3] if recent_news else 'None available'}

Provide a sentiment score from -100 (extremely bearish) to +100 (extremely bullish) and a brief explanation."""

        try:
            response = await asyncio.to_thread(
                self._client.generate_content, prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini sentiment analysis failed: {e}")
            return None

    async def generate_trade_plan(
        self,
        symbol: str,
        indicators: dict,
        account_balance: float,
        risk_tolerance: str = "medium",
    ) -> Optional[str]:
        """Generate a detailed trade plan."""
        if not self._available or not self._client:
            return None

        prompt = f"""Generate a detailed trade plan for {symbol}.

Current Indicators:
{json.dumps(indicators, indent=2)}

Account Balance: ${account_balance:.2f}
Risk Tolerance: {risk_tolerance}

Provide:
1. Direction (Long/Short)
2. Entry price range
3. Stop loss level
4. Take profit targets (TP1, TP2, TP3)
5. Position size recommendation
6. Leverage suggestion
7. Time frame for the trade
8. Risk management rules"""

        try:
            response = await asyncio.to_thread(
                self._client.generate_content, prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini trade plan failed: {e}")
            return None

    def _parse_gemini_response(self, text: str) -> AIAnalysis:
        """Parse Gemini response."""
        text_lower = text.lower()

        # Determine direction
        if "up" in text_lower or "bullish" in text_lower or "buy" in text_lower:
            decision = "buy"
        elif "down" in text_lower or "bearish" in text_lower or "sell" in text_lower:
            decision = "sell"
        else:
            decision = "hold"

        # Estimate confidence from language
        confidence = 0.6  # Default
        if "high confidence" in text_lower or "strong" in text_lower:
            confidence = 0.8
        elif "low confidence" in text_lower or "uncertain" in text_lower:
            confidence = 0.4

        return AIAnalysis(
            model="gemini",
            decision=decision,
            confidence=confidence,
            reasoning=text[:500],
            key_factors=[],
            risk_assessment="medium",
        )


class AIEnsemble:
    """
    Combines LongCat and Gemini analysis for higher accuracy.
    Weighted voting system with confidence thresholds.
    """

    def __init__(self):
        self.longcat = LongCatAI()
        self.gemini = GeminiAI()

    async def initialize(self):
        """Initialize all AI models."""
        await self.gemini.initialize()

    async def get_consensus_signal(
        self,
        symbol: str,
        indicators: dict,
        market_context: dict,
        ohlcv_data: List[Dict] = None,
    ) -> Optional[AIAnalysis]:
        """
        Get consensus signal from both AI models.
        Weights Gemini slightly higher for price prediction,
        LongCat for risk management.
        """
        # Get both analyses concurrently
        longcat_task = self.longcat.analyze_market(symbol, indicators, market_context)
        gemini_task = self.gemini.predict_price_movement(symbol, ohlcv_data or [], indicators)

        longcat_result, gemini_result = await asyncio.gather(
            longcat_task, gemini_task, return_exceptions=True
        )

        # Handle failures
        if isinstance(longcat_result, Exception) or longcat_result is None:
            if isinstance(gemini_result, AIAnalysis):
                return gemini_result
            return None

        if isinstance(gemini_result, Exception) or gemini_result is None:
            return longcat_result

        # Weighted ensemble (Gemini: 55%, LongCat: 45%)
        weight_gemini = 0.55
        weight_longcat = 0.45

        # Decision voting
        scores = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        scores[gemini_result.decision] += gemini_result.confidence * weight_gemini
        scores[longcat_result.decision] += longcat_result.confidence * weight_longcat

        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        # Winner
        best_decision = max(scores, key=scores.get)
        ensemble_confidence = scores[best_decision]

        # Combined reasoning
        reasoning = f"Gemini: {gemini_result.reasoning[:200]} | LongCat: {longcat_result.reasoning[:200]}"

        return AIAnalysis(
            model="ensemble",
            decision=best_decision,
            confidence=ensemble_confidence,
            reasoning=reasoning,
            key_factors=gemini_result.key_factors + longcat_result.key_factors,
            risk_assessment=longcat_result.risk_assessment,
        )


# Singleton instances
longcat_ai = LongCatAI()
gemini_ai = GeminiAI()
ai_ensemble = AIEnsemble()
