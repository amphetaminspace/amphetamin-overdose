"""
Real-time market data fetcher with caching.
Supports multiple exchanges via CCXT unified API.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import ccxt.async_support as ccxt
import pandas as pd
from loguru import logger

from config.settings import settings


class MarketDataFetcher:
    """Fetches and caches OHLCV data from exchanges."""

    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_ttl = 30  # seconds

    async def initialize(self):
        """Initialize exchange connections."""
        # Binance
        if settings.binance_api_key:
            self.exchanges["binance"] = ccxt.binance(settings.binance_config)
            if settings.binance_testnet:
                self.exchanges["binance"].set_sandbox_mode(True)
            await self.exchanges["binance"].load_markets()
            logger.info("Binance exchange initialized")

        # Alpaca (via CCXT if available, else custom)
        # Note: Alpaca has limited crypto; we use it for stock signals if needed

        logger.info(f"Initialized {len(self.exchanges)} exchanges")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 500,
        exchange_name: str = "binance",
    ) -> pd.DataFrame:
        """Fetch OHLCV data as a DataFrame."""
        cache_key = f"{exchange_name}:{symbol}:{timeframe}"
        now = datetime.utcnow()

        # Check cache
        if cache_key in self._cache:
            cached_df, cached_time = self._cache[cache_key]
            if (now - cached_time).seconds < self._cache_ttl:
                return cached_df

        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not initialized")

        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)

            self._cache[cache_key] = (df, now)
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    async def fetch_ticker(self, symbol: str, exchange_name: str = "binance") -> dict:
        """Fetch current ticker data."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return {}
        try:
            return await exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return {}

    async def fetch_multiple_ohlcv(
        self,
        symbols: List[str],
        timeframe: str = "1m",
        limit: int = 500,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV for multiple symbols concurrently."""
        tasks = [self.fetch_ohlcv(symbol, timeframe, limit) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, pd.DataFrame) and not result.empty:
                data[symbol] = result
            elif isinstance(result, Exception):
                logger.warning(f"Failed to fetch {symbol}: {result}")

        return data

    async def get_top_volume_pairs(
        self,
        quote_asset: str = "USDT",
        limit: int = 50,
    ) -> List[dict]:
        """Get top trading pairs by volume for screening."""
        exchange = self.exchanges.get("binance")
        if not exchange:
            return []

        try:
            tickers = await exchange.fetch_tickers()
            pairs = []
            for symbol, ticker in tickers.items():
                if symbol.endswith(quote_asset) and ticker.get("quoteVolume"):
                    pairs.append({
                        "symbol": symbol,
                        "volume_24h": ticker["quoteVolume"],
                        "change_24h": ticker.get("percentage", 0),
                        "bid": ticker.get("bid", 0),
                        "ask": ticker.get("ask", 0),
                        "spread_pct": (
                            (ticker["ask"] - ticker["bid"]) / ticker["bid"] * 100
                            if ticker.get("bid") and ticker.get("ask")
                            else 0
                        ),
                    })

            # Sort by volume descending
            pairs.sort(key=lambda x: x["volume_24h"], reverse=True)
            return pairs[:limit]
        except Exception as e:
            logger.error(f"Error fetching top pairs: {e}")
            return []

    async def close(self):
        """Close all exchange connections."""
        for exchange in self.exchanges.values():
            await exchange.close()
        logger.info("All exchange connections closed")


market_fetcher = MarketDataFetcher()
