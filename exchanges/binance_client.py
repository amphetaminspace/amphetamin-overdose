"""
Binance Exchange Client.
Handles order execution, position management, and account queries.
Supports both spot and futures (margin/leverage) trading.
"""
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

import ccxt.async_support as ccxt

from config.settings import settings


@dataclass
class OrderResult:
    """Result of an order placement."""
    success: bool
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    leverage: float
    status: str
    error: str = ""
    raw: Dict = None


@dataclass
class Position:
    """Current position info."""
    symbol: str
    side: str  # long, short
    quantity: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: float
    margin: float
    liquidation_price: float


class BinanceClient:
    """Async Binance client for trading operations."""

    def __init__(self):
        self.exchange: Optional[ccxt.binance] = None
        self.is_futures = True

    async def connect(self):
        """Connect to Binance."""
        config = settings.binance_config
        self.exchange = ccxt.binance(config)

        if settings.binance_testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("Connected to Binance TESTNET")
        else:
            logger.info("Connected to Binance LIVE")

        await self.exchange.load_markets()
        logger.info(f"Loaded {len(self.exchange.markets)} markets")

    async def get_account_balance(self) -> Dict:
        """Get account balance."""
        try:
            balance = await self.exchange.fetch_balance()
            return {
                "total_equity": balance.get("USDT", {}).get("total", 0),
                "available": balance.get("USDT", {}).get("free", 0),
                "used_margin": balance.get("USDT", {}).get("used", 0),
                "total_wallet": balance.get("total", {}).get("USDT", 0),
            }
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return {"total_equity": 0, "available": 0, "used_margin": 0}

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        try:
            positions = await self.exchange.fetch_positions()
            result = []
            for pos in positions:
                if abs(float(pos.get("contracts", 0))) > 0:
                    result.append(Position(
                        symbol=pos["symbol"],
                        side="long" if pos["side"] == "long" else "short",
                        quantity=abs(float(pos.get("contracts", 0))),
                        entry_price=float(pos.get("entryPrice", 0)),
                        mark_price=float(pos.get("markPrice", 0)),
                        unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                        leverage=float(pos.get("leverage", 1)),
                        margin=float(pos.get("initialMargin", 0)),
                        liquidation_price=float(pos.get("liquidationPrice", 0)),
                    ))
            return result
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: float) -> bool:
        """Set leverage for a symbol."""
        try:
            leverage = min(leverage, settings.max_leverage)
            await self.exchange.set_leverage(int(leverage), symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return False

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        leverage: float = 1.0,
    ) -> OrderResult:
        """Place a market order."""
        try:
            # Set leverage first
            await self.set_leverage(symbol, leverage)

            order = await self.exchange.create_market_buy_order(symbol, quantity) if side == "buy" \
                else await self.exchange.create_market_sell_order(symbol, quantity)

            return OrderResult(
                success=True,
                order_id=str(order["id"]),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=float(order.get("price", 0) or order.get("average", 0)),
                leverage=leverage,
                status=order.get("status", "filled"),
                raw=order,
            )
        except Exception as e:
            logger.error(f"Market order failed for {symbol}: {e}")
            return OrderResult(
                success=False, order_id="", symbol=symbol, side=side,
                quantity=quantity, price=0, leverage=leverage,
                status="failed", error=str(e),
            )

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        leverage: float = 1.0,
    ) -> OrderResult:
        """Place a limit order."""
        try:
            await self.set_leverage(symbol, leverage)
            order = await self.exchange.create_limit_buy_order(symbol, quantity, price) if side == "buy" \
                else await self.exchange.create_limit_sell_order(symbol, quantity, price)

            return OrderResult(
                success=True,
                order_id=str(order["id"]),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                leverage=leverage,
                status=order.get("status", "open"),
                raw=order,
            )
        except Exception as e:
            logger.error(f"Limit order failed for {symbol}: {e}")
            return OrderResult(
                success=False, order_id="", symbol=symbol, side=side,
                quantity=quantity, price=price, leverage=leverage,
                status="failed", error=str(e),
            )

    async def place_stop_loss(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> OrderResult:
        """Place a stop-loss order."""
        try:
            # For futures, use stop market order
            order = await self.exchange.create_order(
                symbol=symbol,
                type="stop_market",
                side="sell" if side == "buy" else "buy",
                amount=quantity,
                params={"stopPrice": stop_price},
            )
            return OrderResult(
                success=True,
                order_id=str(order["id"]),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=stop_price,
                leverage=1,
                status="open",
                raw=order,
            )
        except Exception as e:
            logger.error(f"Stop loss failed for {symbol}: {e}")
            return OrderResult(
                success=False, order_id="", symbol=symbol, side=side,
                quantity=quantity, price=stop_price, leverage=1,
                status="failed", error=str(e),
            )

    async def place_take_profit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        tp_price: float,
    ) -> OrderResult:
        """Place a take-profit order."""
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type="take_profit_market",
                side="sell" if side == "buy" else "buy",
                amount=quantity,
                params={"stopPrice": tp_price},
            )
            return OrderResult(
                success=True,
                order_id=str(order["id"]),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=tp_price,
                leverage=1,
                status="open",
                raw=order,
            )
        except Exception as e:
            logger.error(f"Take profit failed for {symbol}: {e}")
            return OrderResult(
                success=False, order_id="", symbol=symbol, side=side,
                quantity=quantity, price=tp_price, leverage=1,
                status="failed", error=str(e),
            )

    async def place_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        leverage: float = 1.0,
    ) -> Dict[str, OrderResult]:
        """Place entry + stop loss + take profit as bracket."""
        results = {"entry": None, "stop_loss": None, "take_profit": None}

        # Entry order
        results["entry"] = await self.place_limit_order(
            symbol, side, quantity, entry_price, leverage
        )

        if results["entry"].success:
            # Stop loss
            results["stop_loss"] = await self.place_stop_loss(
                symbol, side, quantity, stop_loss
            )
            # Take profit
            results["take_profit"] = await self.place_take_profit(
                symbol, side, quantity, take_profit
            )

        return results

    async def close_position(self, symbol: str) -> OrderResult:
        """Close all positions for a symbol."""
        try:
            positions = await self.get_positions()
            for pos in positions:
                if pos.symbol == symbol:
                    close_side = "sell" if pos.side == "long" else "buy"
                    return await self.place_market_order(
                        symbol, close_side, pos.quantity, pos.leverage
                    )
            return OrderResult(
                success=False, order_id="", symbol=symbol, side="",
                quantity=0, price=0, leverage=1, status="no_position",
            )
        except Exception as e:
            logger.error(f"Failed to close position for {symbol}:{e}")
            return OrderResult(
                success=False, order_id="", symbol=symbol, side="",
                quantity=0, price=0, leverage=1, status="failed", error=str(e),
            )

    async def cancel_all_orders(self, symbol: str):
        """Cancel all open orders for a symbol."""
        try:
            await self.exchange.cancel_all_orders(symbol)
            logger.info(f"Cancelled all orders for {symbol}")
        except Exception as e:
            logger.error(f"Failed to cancel orders for {symbol}: {e}")

    async def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """Get order status."""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return {
                "status": order.get("status", ""),
                "filled": order.get("filled", 0),
                "remaining": order.get("remaining", 0),
                "price": order.get("price", 0),
            }
        except Exception as e:
            logger.error(f"Failed to fetch order status: {e}")
            return {"status": "unknown"}

    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            logger.info("Binance connection closed")


binance_client = BinanceClient()
