"""
Arbitrage Bot Configuration
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PolymarketConfig:
    """Polymarket API configuration."""
    api_url: str = "https://clob.polymarket.com"
    ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    chain_id: int = 137  # Polygon
    # Set these via environment variables
    private_key: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_passphrase: Optional[str] = None

    def __post_init__(self):
        self.private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        self.api_key = os.getenv("POLYMARKET_API_KEY")
        self.api_secret = os.getenv("POLYMARKET_API_SECRET")
        self.api_passphrase = os.getenv("POLYMARKET_API_PASSPHRASE")


@dataclass
class KalshiConfig:
    """Kalshi API configuration."""
    api_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    ws_url: str = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    # Set these via environment variables
    email: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        self.email = os.getenv("KALSHI_EMAIL")
        self.password = os.getenv("KALSHI_PASSWORD")
        self.api_key = os.getenv("KALSHI_API_KEY")


@dataclass
class TradingConfig:
    """Trading parameters."""
    # Minimum spread to consider (as decimal, 0.01 = 1%)
    min_spread: float = 0.01
    # Maximum position size per trade (USD)
    max_position: float = 100.0
    # Minimum position size (USD)
    min_position: float = 10.0
    # Maximum total exposure (USD)
    max_exposure: float = 500.0
    # Slippage tolerance (as decimal)
    slippage_tolerance: float = 0.005
    # Only trade markets expiring within this many hours
    max_hours_to_expiry: int = 72
    # Minimum hours to expiry (avoid last-minute resolution risk)
    min_hours_to_expiry: int = 1
    # Paper trading mode (no real trades)
    paper_trading: bool = True


@dataclass
class BotConfig:
    """Main bot configuration."""
    polymarket: PolymarketConfig
    kalshi: KalshiConfig
    trading: TradingConfig
    # Polling interval in seconds
    poll_interval: float = 1.0
    # Log file path
    log_file: str = "arbitrage_bot.log"
    # Database for trade history
    db_path: str = "trades.db"


def load_config() -> BotConfig:
    """Load configuration from environment."""
    return BotConfig(
        polymarket=PolymarketConfig(),
        kalshi=KalshiConfig(),
        trading=TradingConfig()
    )


# Environment variable template
ENV_TEMPLATE = """
# Polymarket (requires crypto wallet)
POLYMARKET_PRIVATE_KEY=your_wallet_private_key
POLYMARKET_API_KEY=your_api_key
POLYMARKET_API_SECRET=your_api_secret
POLYMARKET_API_PASSPHRASE=your_passphrase

# Kalshi (US regulated, requires account)
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_API_KEY=your_api_key
"""

if __name__ == "__main__":
    print("Environment template for .env file:")
    print(ENV_TEMPLATE)
