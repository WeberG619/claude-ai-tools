"""
Market Connectors - Interface with Polymarket and Kalshi APIs.
"""
import asyncio
import aiohttp
import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


@dataclass
class MarketData:
    """Standardized market data across platforms."""
    platform: str
    market_id: str
    question: str
    yes_price: float
    no_price: float
    yes_volume: float
    no_volume: float
    expires_at: Optional[datetime]
    category: str
    last_updated: datetime


@dataclass
class OrderResult:
    """Result of an order placement."""
    success: bool
    order_id: Optional[str]
    filled_price: Optional[float]
    filled_amount: Optional[float]
    error: Optional[str]


class MarketConnector(ABC):
    """Abstract base class for market connectors."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the platform."""
        pass

    @abstractmethod
    async def get_markets(self, category: str = None) -> List[MarketData]:
        """Get available markets."""
        pass

    @abstractmethod
    async def get_market_price(self, market_id: str) -> MarketData:
        """Get current price for a specific market."""
        pass

    @abstractmethod
    async def place_order(self, market_id: str, side: str,
                          amount: float, price: float) -> OrderResult:
        """Place an order. Side is 'yes' or 'no'."""
        pass

    @abstractmethod
    async def get_balance(self) -> float:
        """Get available balance."""
        pass


class PolymarketConnector(MarketConnector):
    """Connector for Polymarket CLOB API."""

    def __init__(self, config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated = False

    async def connect(self) -> bool:
        """Connect to Polymarket API."""
        self.session = aiohttp.ClientSession()

        # Test connection
        try:
            async with self.session.get(f"{self.config.api_url}/markets") as resp:
                if resp.status == 200:
                    print("Polymarket: Connected successfully")
                    return True
        except Exception as e:
            print(f"Polymarket connection failed: {e}")

        return False

    async def get_markets(self, category: str = None) -> List[MarketData]:
        """Get active markets from Polymarket."""
        markets = []

        try:
            params = {"active": "true", "limit": 100}
            if category:
                params["tag"] = category

            async with self.session.get(
                f"{self.config.api_url}/markets",
                params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    for m in data:
                        # Polymarket uses token structure
                        tokens = m.get("tokens", [])
                        yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
                        no_token = next((t for t in tokens if t.get("outcome") == "No"), None)

                        if yes_token and no_token:
                            markets.append(MarketData(
                                platform="polymarket",
                                market_id=m.get("condition_id", ""),
                                question=m.get("question", ""),
                                yes_price=float(yes_token.get("price", 0)),
                                no_price=float(no_token.get("price", 0)),
                                yes_volume=float(m.get("volume", 0)),
                                no_volume=float(m.get("volume", 0)),
                                expires_at=self._parse_date(m.get("end_date_iso")),
                                category=m.get("tags", [""])[0] if m.get("tags") else "",
                                last_updated=datetime.now()
                            ))
        except Exception as e:
            print(f"Polymarket get_markets error: {e}")

        return markets

    async def get_market_price(self, market_id: str) -> Optional[MarketData]:
        """Get current price for a specific market."""
        try:
            async with self.session.get(
                f"{self.config.api_url}/markets/{market_id}"
            ) as resp:
                if resp.status == 200:
                    m = await resp.json()
                    tokens = m.get("tokens", [])
                    yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
                    no_token = next((t for t in tokens if t.get("outcome") == "No"), None)

                    if yes_token and no_token:
                        return MarketData(
                            platform="polymarket",
                            market_id=market_id,
                            question=m.get("question", ""),
                            yes_price=float(yes_token.get("price", 0)),
                            no_price=float(no_token.get("price", 0)),
                            yes_volume=float(m.get("volume", 0)),
                            no_volume=float(m.get("volume", 0)),
                            expires_at=self._parse_date(m.get("end_date_iso")),
                            category="",
                            last_updated=datetime.now()
                        )
        except Exception as e:
            print(f"Polymarket get_market_price error: {e}")

        return None

    async def place_order(self, market_id: str, side: str,
                          amount: float, price: float) -> OrderResult:
        """Place order on Polymarket."""
        # TODO: Implement actual order placement with signing
        # This requires CLOB API authentication and transaction signing
        return OrderResult(
            success=False,
            order_id=None,
            filled_price=None,
            filled_amount=None,
            error="Order placement not implemented - paper trading only"
        )

    async def get_balance(self) -> float:
        """Get USDC balance."""
        # TODO: Implement balance check via wallet
        return 0.0

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


class KalshiConnector(MarketConnector):
    """Connector for Kalshi API."""

    def __init__(self, config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None

    async def connect(self) -> bool:
        """Connect and authenticate to Kalshi API."""
        self.session = aiohttp.ClientSession()

        # Authenticate
        if self.config.email and self.config.password:
            try:
                async with self.session.post(
                    f"{self.config.api_url}/login",
                    json={
                        "email": self.config.email,
                        "password": self.config.password
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.token = data.get("token")
                        print("Kalshi: Authenticated successfully")
                        return True
                    else:
                        print(f"Kalshi auth failed: {resp.status}")
            except Exception as e:
                print(f"Kalshi connection failed: {e}")

        # Try unauthenticated access for market data
        print("Kalshi: Using unauthenticated access (read-only)")
        return True

    async def get_markets(self, category: str = None) -> List[MarketData]:
        """Get active markets from Kalshi."""
        markets = []

        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            params = {"status": "open", "limit": 100}
            if category:
                params["series_ticker"] = category

            async with self.session.get(
                f"{self.config.api_url}/markets",
                headers=headers,
                params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    for m in data.get("markets", []):
                        markets.append(MarketData(
                            platform="kalshi",
                            market_id=m.get("ticker", ""),
                            question=m.get("title", ""),
                            yes_price=float(m.get("yes_ask", 0)) / 100,  # Kalshi uses cents
                            no_price=float(m.get("no_ask", 0)) / 100,
                            yes_volume=float(m.get("volume", 0)),
                            no_volume=float(m.get("volume", 0)),
                            expires_at=self._parse_date(m.get("close_time")),
                            category=m.get("series_ticker", ""),
                            last_updated=datetime.now()
                        ))
        except Exception as e:
            print(f"Kalshi get_markets error: {e}")

        return markets

    async def get_market_price(self, market_id: str) -> Optional[MarketData]:
        """Get current price for a specific market."""
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            async with self.session.get(
                f"{self.config.api_url}/markets/{market_id}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    m = await resp.json()
                    market = m.get("market", {})

                    return MarketData(
                        platform="kalshi",
                        market_id=market_id,
                        question=market.get("title", ""),
                        yes_price=float(market.get("yes_ask", 0)) / 100,
                        no_price=float(market.get("no_ask", 0)) / 100,
                        yes_volume=float(market.get("volume", 0)),
                        no_volume=float(market.get("volume", 0)),
                        expires_at=self._parse_date(market.get("close_time")),
                        category=market.get("series_ticker", ""),
                        last_updated=datetime.now()
                    )
        except Exception as e:
            print(f"Kalshi get_market_price error: {e}")

        return None

    async def place_order(self, market_id: str, side: str,
                          amount: float, price: float) -> OrderResult:
        """Place order on Kalshi."""
        if not self.token:
            return OrderResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                error="Not authenticated"
            )

        # TODO: Implement actual order placement
        return OrderResult(
            success=False,
            order_id=None,
            filled_price=None,
            filled_amount=None,
            error="Order placement not implemented - paper trading only"
        )

    async def get_balance(self) -> float:
        """Get USD balance."""
        if not self.token:
            return 0.0

        try:
            async with self.session.get(
                f"{self.config.api_url}/portfolio/balance",
                headers={"Authorization": f"Bearer {self.token}"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data.get("balance", 0)) / 100  # Cents to dollars
        except Exception as e:
            print(f"Kalshi get_balance error: {e}")

        return 0.0

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
