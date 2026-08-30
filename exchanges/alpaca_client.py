"""
Alpaca Exchange Client.
Used for stock/ETF signals and as a secondary crypto connector.
"""
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

from config.settings import settings


@dataclass
class AlpacaPosition:
    """Alpaca position info."""
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    market_value: float


class AlpacaClient:
    """Alpaca trading client."""

    def __init__(self):
        self.api = None
        self._available = bool(settings.alpaca_api_key)

    async def connect(self):
        """Connect to Alpaca."""
        if not self._available:
            logger.warning("Alpaca API key not configured")
            return

        try:
            import alpaca_trade_api as tradeapi
            self.api = tradeapi.REST(
                key_id=settings.alpaca_api_key,
                secret_key=settings.alpaca_api_secret,
                base_url=settings.alpaca_base_url,
            )
            account = self.api.get_account()
            logger.info(f"Alpaca connected. Account status: {account.status}")
        except ImportError:
            logger.warning("alpaca-trade-api not installed")
            self._available = False
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            self._available = False

    async def get_account_balance(self) -> Dict:
        """Get account balance."""
        if not self._available or not self.api:
            return {"total_equity": 0, "available": 0, "buying_power": 0}

        try:
            account = self.api.get_account()
            return {
                "total_equity": float(account.equity),
                "available": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
            }
        except Exception as e:
            logger.error(f"Failed to fetch Alpaca balance: {e}")
            return {"total_equity": 0, "available": 0, "buying_power": 0}

    async def get_positions(self) -> List[AlpacaPosition]:
        """Get all open positions."""
        if not self._available or not self.api:
            return []

        try:
            positions = self.api.list_positions()
            return [
                AlpacaPosition(
                    symbol=p.symbol,
                    side="long" if p.side == "long" else "short",
                    quantity=float(p.qty),
                    entry_price=float(p.avg_entry_price),
                    current_price=float(p.current_price),
                    unrealized_pnl=float(p.unrealized_pl),
                    market_value=float(p.market_value),
                )
                for p in positions
            ]
        except Exception as e:
            logger.error(f"Failed to fetch Alpaca positions: {e}")
            return []

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: float = None,
        stop_loss: Dict = None,
        take_profit: float = None,
    ) -> Dict:
        """Place an order on Alpaca."""
        if not self._available or not self.api:
            return {"success": False, "error": "Alpaca not available"}

        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type=order_type,
                time_in_force="day",
                limit_price=limit_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            return {
                "success": True,
                "order_id": order.id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "status": order.status,
            }
        except Exception as e:
            logger.error(f"Alpaca order failed: {e}")
            return {"success": False, "error": str(e)}

    async def close_position(self, symbol: str) -> Dict:
        """Close a position."""
        if not self._available or not self.api:
            return {"success": False}

        try:
            order = self.api.close_position(symbol)
            return {"success": True, "order_id": order.id if order else ""}
        except Exception as e:
            logger.error(f"Failed to close Alpaca position: {e}")
            return {"success": False, "error": str(e)}

    async def get_crypto_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        limit: int = 100,
    ) -> List[Dict]:
        """Get crypto OHLCV bars from Alpaca."""
        if not self._available or not self.api:
            return []

        try:
            bars = self.api.get_crypto_bars(symbol, timeframe, limit=limit)
            return [
                {
                    "timestamp": str(b.t),
                    "open": b.o,
                    "high": b.h,
                    "low": b.l,
                    "close": b.c,
                    "volume": b.v,
                }
                for b in bars[df.symbol]
            ]
        except Exception as e:
            logger.error(f"Failed to fetch crypto bars: {e}")
            return []


alpaca_client = AlpacaClient()
