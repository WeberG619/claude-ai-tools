"""
Arbitrage Detector - Finds profitable spreads between prediction markets.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from market_connector import MarketData


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity."""
    # Market info
    question: str
    polymarket_id: str
    kalshi_id: str

    # Prices
    poly_yes: float
    poly_no: float
    kalshi_yes: float
    kalshi_no: float

    # Best arbitrage combination
    strategy: str  # "poly_yes_kalshi_no" or "poly_no_kalshi_yes"
    total_cost: float  # Cost to buy both sides
    profit_percent: float  # Guaranteed profit as percentage
    profit_dollars: float  # Profit per $100 wagered

    # Metadata
    expires_at: Optional[datetime]
    detected_at: datetime
    confidence: float  # Match confidence between markets


class ArbitrageDetector:
    """Detects arbitrage opportunities across prediction markets."""

    def __init__(self, min_spread: float = 0.01, min_confidence: float = 0.85):
        """
        Initialize detector.

        Args:
            min_spread: Minimum profit spread to consider (0.01 = 1%)
            min_confidence: Minimum question match confidence (0.85 = 85%)
        """
        self.min_spread = min_spread
        self.min_confidence = min_confidence
        self.matched_markets: Dict[str, Tuple[str, str]] = {}  # Cache market matches

    def find_opportunities(
        self,
        polymarket_data: List[MarketData],
        kalshi_data: List[MarketData]
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities between two market lists.

        Returns:
            List of profitable opportunities sorted by profit percentage.
        """
        opportunities = []

        for poly in polymarket_data:
            # Find matching Kalshi market
            kalshi_match, confidence = self._find_matching_market(poly, kalshi_data)

            if not kalshi_match or confidence < self.min_confidence:
                continue

            # Check for arbitrage
            opp = self._check_arbitrage(poly, kalshi_match, confidence)
            if opp:
                opportunities.append(opp)

        # Sort by profit percentage descending
        opportunities.sort(key=lambda x: x.profit_percent, reverse=True)
        return opportunities

    def _find_matching_market(
        self,
        poly: MarketData,
        kalshi_markets: List[MarketData]
    ) -> Tuple[Optional[MarketData], float]:
        """
        Find the matching Kalshi market for a Polymarket question.

        Uses fuzzy string matching on the question text.
        """
        # Check cache first
        cache_key = poly.market_id
        if cache_key in self.matched_markets:
            kalshi_id, confidence = self.matched_markets[cache_key]
            kalshi = next((k for k in kalshi_markets if k.market_id == kalshi_id), None)
            if kalshi:
                return kalshi, confidence

        best_match = None
        best_score = 0.0

        poly_question = self._normalize_question(poly.question)

        for kalshi in kalshi_markets:
            kalshi_question = self._normalize_question(kalshi.question)

            # Calculate similarity
            score = SequenceMatcher(None, poly_question, kalshi_question).ratio()

            # Boost score if categories match
            if poly.category and kalshi.category:
                if poly.category.lower() in kalshi.category.lower() or \
                   kalshi.category.lower() in poly.category.lower():
                    score += 0.1

            if score > best_score:
                best_score = score
                best_match = kalshi

        # Cache the match
        if best_match and best_score >= self.min_confidence:
            self.matched_markets[cache_key] = (best_match.market_id, best_score)

        return best_match, best_score

    def _normalize_question(self, question: str) -> str:
        """Normalize question text for matching."""
        # Lowercase
        q = question.lower()

        # Remove common words that don't affect meaning
        remove_words = ["will", "the", "a", "an", "be", "to", "in", "on", "at", "by", "?"]
        for word in remove_words:
            q = q.replace(f" {word} ", " ")

        # Remove extra spaces
        q = " ".join(q.split())

        return q

    def _check_arbitrage(
        self,
        poly: MarketData,
        kalshi: MarketData,
        confidence: float
    ) -> Optional[ArbitrageOpportunity]:
        """
        Check if there's a profitable arbitrage between two markets.

        Arbitrage exists when:
        - Poly YES + Kalshi NO < 1.00, or
        - Poly NO + Kalshi YES < 1.00
        """
        now = datetime.now()

        # Strategy 1: Buy YES on Polymarket, NO on Kalshi
        cost1 = poly.yes_price + kalshi.no_price
        profit1 = 1.0 - cost1 if cost1 < 1.0 else 0

        # Strategy 2: Buy NO on Polymarket, YES on Kalshi
        cost2 = poly.no_price + kalshi.yes_price
        profit2 = 1.0 - cost2 if cost2 < 1.0 else 0

        # Choose better strategy
        if profit1 > profit2 and profit1 >= self.min_spread:
            return ArbitrageOpportunity(
                question=poly.question,
                polymarket_id=poly.market_id,
                kalshi_id=kalshi.market_id,
                poly_yes=poly.yes_price,
                poly_no=poly.no_price,
                kalshi_yes=kalshi.yes_price,
                kalshi_no=kalshi.no_price,
                strategy="poly_yes_kalshi_no",
                total_cost=cost1,
                profit_percent=profit1 * 100,
                profit_dollars=profit1 * 100,  # Per $100 wagered
                expires_at=poly.expires_at or kalshi.expires_at,
                detected_at=now,
                confidence=confidence
            )
        elif profit2 >= self.min_spread:
            return ArbitrageOpportunity(
                question=poly.question,
                polymarket_id=poly.market_id,
                kalshi_id=kalshi.market_id,
                poly_yes=poly.yes_price,
                poly_no=poly.no_price,
                kalshi_yes=kalshi.yes_price,
                kalshi_no=kalshi.no_price,
                strategy="poly_no_kalshi_yes",
                total_cost=cost2,
                profit_percent=profit2 * 100,
                profit_dollars=profit2 * 100,
                expires_at=poly.expires_at or kalshi.expires_at,
                detected_at=now,
                confidence=confidence
            )

        return None

    def format_opportunity(self, opp: ArbitrageOpportunity) -> str:
        """Format an opportunity for display."""
        lines = [
            f"\n{'='*60}",
            f"ARBITRAGE OPPORTUNITY DETECTED",
            f"{'='*60}",
            f"Question: {opp.question[:80]}...",
            f"Match Confidence: {opp.confidence*100:.1f}%",
            f"",
            f"Polymarket: YES={opp.poly_yes:.3f} NO={opp.poly_no:.3f}",
            f"Kalshi:     YES={opp.kalshi_yes:.3f} NO={opp.kalshi_no:.3f}",
            f"",
            f"Strategy: {opp.strategy}",
            f"Total Cost: ${opp.total_cost:.3f}",
            f"PROFIT: {opp.profit_percent:.2f}% (${opp.profit_dollars:.2f} per $100)",
            f"",
            f"Expires: {opp.expires_at.strftime('%Y-%m-%d %H:%M') if opp.expires_at else 'Unknown'}",
            f"{'='*60}",
        ]
        return "\n".join(lines)
