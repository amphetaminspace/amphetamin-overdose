"""
amphetamin_Overdose - Global Configuration
All settings centralized here with validation via Pydantic.
"""
import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────
    database_url: str = Field(default="postgresql://trader:trader@localhost:5432/amphetamin_overdose")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Binance ───────────────────────────────────────
    binance_api_key: str = Field(default="")
    binance_api_secret: str = Field(default="")
    binance_testnet: bool = Field(default=True)

    # ── Alpaca ────────────────────────────────────────
    alpaca_api_key: str = Field(default="")
    alpaca_api_secret: str = Field(default="")
    alpaca_base_url: str = Field(default="https://paper-api.alpaca.markets")

    # ── AI Keys ───────────────────────────────────────
    longcat_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")

    # ── Trading Parameters ────────────────────────────
    max_pairs: int = Field(default=32, ge=1, le=64)
    max_leverage: float = Field(default=25.0, ge=1.0, le=125.0)
    risk_per_trade: float = Field(default=0.02, ge=0.001, le=0.5)
    daily_loss_limit: float = Field(default=0.05, ge=0.01, le=0.5)
    target_daily_return: float = Field(default=0.10, ge=0.01, le=10.0)
    max_open_positions: int = Field(default=10, ge=1, le=32)
    scalping_timeframe: str = Field(default="1m")
    confirmation_timeframe: str = Field(default="5m")
    trend_timeframe: str = Field(default="15m")

    # ── Risk Management ───────────────────────────────
    stop_loss_pct: float = Field(default=0.015, ge=0.001, le=0.1)
    take_profit_pct: float = Field(default=0.045, ge=0.005, le=0.5)
    trailing_stop_pct: float = Field(default=0.02, ge=0.005, le=0.1)
    trailing_stop_activation: float = Field(default=0.02, ge=0.005, le=0.2)
    max_drawdown_pct: float = Field(default=0.15, ge=0.05, le=0.5)
    kelly_fraction: float = Field(default=0.5, ge=0.1, le=1.0)

    # ── Mode ──────────────────────────────────────────
    paper_trading: bool = Field(default=True)
    strategy_aggressiveness: str = Field(default="high")

    @field_validator("strategy_aggressiveness")
    @classmethod
    def validate_aggressiveness(cls, v):
        allowed = {"low", "medium", "high", "extreme"}
        if v.lower() not in allowed:
            raise ValueError(f"aggressiveness must be one of {allowed}")
        return v.lower()

    @property
    def binance_config(self) -> dict:
        return {
            "apiKey": self.binance_api_key,
            "secret": self.binance_api_secret,
            "sandbox": self.binance_testnet,
            "options": {"defaultType": "future"},
        }


settings = Settings()
