"""
Arbitrage Bot - Main execution loop.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from config import load_config, BotConfig
from market_connector import PolymarketConnector, KalshiConnector, MarketData
from arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity


class ArbitrageBot:
    """Main arbitrage bot."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.polymarket = PolymarketConnector(config.polymarket)
        self.kalshi = KalshiConnector(config.kalshi)
        self.detector = ArbitrageDetector(
            min_spread=config.trading.min_spread
        )
        self.running = False
        self.opportunities_found = 0
        self.total_profit_detected = 0.0

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the arbitrage bot."""
        self.logger.info("Starting Arbitrage Bot...")

        # Connect to markets
        poly_connected = await self.polymarket.connect()
        kalshi_connected = await self.kalshi.connect()

        if not poly_connected:
            self.logger.error("Failed to connect to Polymarket")
        if not kalshi_connected:
            self.logger.error("Failed to connect to Kalshi")

        if not (poly_connected or kalshi_connected):
            self.logger.error("Cannot proceed without at least one market connection")
            return

        self.running = True
        self.logger.info(f"Bot started. Paper trading: {self.config.trading.paper_trading}")
        self.logger.info(f"Min spread: {self.config.trading.min_spread*100:.1f}%")
        self.logger.info(f"Max position: ${self.config.trading.max_position}")

        # Main loop
        try:
            while self.running:
                await self._scan_cycle()
                await asyncio.sleep(self.config.poll_interval)
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the bot and cleanup."""
        self.running = False
        await self.polymarket.close()
        await self.kalshi.close()

        self.logger.info(f"Bot stopped. Opportunities found: {self.opportunities_found}")
        self.logger.info(f"Total theoretical profit: ${self.total_profit_detected:.2f}")

    async def _scan_cycle(self):
        """Single scan cycle to find opportunities."""
        try:
            # Fetch market data
            poly_markets = await self.polymarket.get_markets()
            kalshi_markets = await self.kalshi.get_markets()

            self.logger.debug(f"Fetched {len(poly_markets)} Polymarket, {len(kalshi_markets)} Kalshi markets")

            # Find opportunities
            opportunities = self.detector.find_opportunities(poly_markets, kalshi_markets)

            # Process opportunities
            for opp in opportunities:
                self.opportunities_found += 1
                self.total_profit_detected += opp.profit_dollars

                # Log the opportunity
                self.logger.info(self.detector.format_opportunity(opp))

                # Execute trade if not paper trading
                if not self.config.trading.paper_trading:
                    await self._execute_arbitrage(opp)
                else:
                    self.logger.info("[PAPER] Would execute this trade")

        except Exception as e:
            self.logger.error(f"Error in scan cycle: {e}")

    async def _execute_arbitrage(self, opp: ArbitrageOpportunity):
        """
        Execute an arbitrage trade.

        IMPORTANT: Real money implementation requires careful
        handling of order execution, slippage, and timing.
        """
        self.logger.warning("LIVE TRADING NOT IMPLEMENTED - Paper mode only")

        # TODO: Implement real execution:
        # 1. Verify prices haven't moved
        # 2. Calculate exact position sizes
        # 3. Place orders on both platforms simultaneously
        # 4. Monitor fill status
        # 5. Handle partial fills
        # 6. Log trade to database

        return False

    async def scan_once(self) -> List[ArbitrageOpportunity]:
        """Run a single scan and return opportunities (for testing)."""
        await self.polymarket.connect()
        await self.kalshi.connect()

        poly_markets = await self.polymarket.get_markets()
        kalshi_markets = await self.kalshi.get_markets()

        opportunities = self.detector.find_opportunities(poly_markets, kalshi_markets)

        await self.polymarket.close()
        await self.kalshi.close()

        return opportunities


async def main():
    """Entry point."""
    config = load_config()
    bot = ArbitrageBot(config)

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         PREDICTION MARKET ARBITRAGE BOT                  ║
    ║                                                          ║
    ║  Scanning Polymarket and Kalshi for price discrepancies  ║
    ║  Press Ctrl+C to stop                                    ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
