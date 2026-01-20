#!/usr/bin/env python3
"""
NOA Matcher - Product Approval Matching for Revit Elements
===========================================================
Matches Revit family types to NOA database products.
Validates NOA numbers and suggests approved alternatives.

In the High-Velocity Hurricane Zone (HVHZ), all exterior products must have
either a Miami-Dade NOA or Florida Product Approval (FL#).

Author: BIM Ops Studio
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Import local modules
try:
    from noa_database import NOADatabase, ProductCategory
except ImportError as e:
    logging.warning(f"Import error: {e}. NOADatabase not available.")
    NOADatabase = None

# Configure logging
logger = logging.getLogger(__name__)


class MatchConfidence(Enum):
    """Confidence level of product match."""
    EXACT = "exact"  # NOA number matches exactly
    HIGH = "high"  # Strong match on manufacturer + model
    MEDIUM = "medium"  # Match on category + specs
    LOW = "low"  # Only category match
    NONE = "none"  # No match found


@dataclass
class NOAValidationResult:
    """Result of NOA validation."""
    noa_number: str
    is_valid: bool
    is_expired: bool
    product_name: Optional[str] = None
    manufacturer: Optional[str] = None
    expiration_date: Optional[str] = None
    category: Optional[str] = None
    design_pressure_positive: Optional[float] = None
    design_pressure_negative: Optional[float] = None
    missile_impact: Optional[str] = None
    message: str = ""


@dataclass
class NOAMatch:
    """A matched NOA product."""
    noa_number: str
    product_name: str
    manufacturer: str
    confidence: MatchConfidence
    category: str
    subcategory: Optional[str] = None
    design_pressure_positive: Optional[float] = None
    design_pressure_negative: Optional[float] = None
    missile_impact: Optional[str] = None
    expiration_date: Optional[str] = None
    match_reason: str = ""


@dataclass
class NOAMatchResult:
    """Result of matching an element to NOA products."""
    element_mark: str
    element_type: str
    category: str
    provided_noa: Optional[str]
    validation: Optional[NOAValidationResult]
    suggested_products: List[NOAMatch]
    best_match: Optional[NOAMatch] = None
    needs_noa: bool = True
    message: str = ""


class NOAMatcher:
    """
    Match Revit family types to NOA database products.

    Provides:
    - Validation of NOA numbers against database
    - Matching family types to approved products
    - Suggestions for NOA-compliant alternatives
    - Expiration checking and warnings

    Example:
        matcher = NOAMatcher()
        result = matcher.match_door_type("PGT", "WinGuard Entry Door")
        if result.best_match:
            print(f"Matched to {result.best_match.noa_number}")
    """

    # Common manufacturer name variations
    MANUFACTURER_ALIASES = {
        "pgt": ["pgt", "pgt industries", "pgt windows", "pgt winguard"],
        "cgi": ["cgi", "cgi windows", "cgi windows & doors", "cgi windows and doors"],
        "es": ["es", "es windows", "es windows and doors"],
        "lawson": ["lawson", "lawson industries", "lawson windows"],
        "ykk": ["ykk", "ykk ap", "ykk ap america"],
        "kolbe": ["kolbe", "kolbe windows", "kolbe windows & doors"],
        "gaf": ["gaf", "gaf roofing", "gaf materials"],
        "certainteed": ["certainteed", "certainteed roofing"],
        "boral": ["boral", "boral roofing", "boral america"],
        "simpson": ["simpson", "simpson strong-tie", "simpson strong tie"],
        "clopay": ["clopay", "clopay garage doors", "clopay doors"],
        "amarr": ["amarr", "amarr garage doors", "amarr doors"],
        "roll-a-way": ["roll-a-way", "rollaway", "roll a way"],
        "hv aluminum": ["hv aluminum", "hv", "hv aluminium"],
    }

    # Product keywords by category
    CATEGORY_KEYWORDS = {
        "windows": ["window", "casement", "single hung", "double hung", "fixed", "picture",
                   "awning", "sliding", "hopper", "jalousie"],
        "doors": ["door", "entry", "french", "sliding glass", "patio", "swing", "hinged"],
        "shutters": ["shutter", "accordion", "roll-down", "rolling", "bahama", "colonial",
                    "storm panel"],
        "garage_doors": ["garage", "overhead", "sectional", "roll-up"],
        "roofing": ["shingle", "tile", "metal roof", "roof", "underlayment"],
        "skylights": ["skylight", "roof window", "tubular", "dome"],
        "fasteners": ["hurricane tie", "strap", "anchor", "hold-down", "connector",
                     "clip", "hanger"],
    }

    def __init__(self, noa_db: NOADatabase = None):
        """
        Initialize the matcher.

        Args:
            noa_db: NOADatabase instance (creates new if None)
        """
        self.noa_db = noa_db or (NOADatabase() if NOADatabase else None)

    def validate_noa_number(self, noa_number: str) -> NOAValidationResult:
        """
        Validate an NOA number against the database.

        Args:
            noa_number: The NOA number to validate (e.g., "NOA 21-0505.05")

        Returns:
            NOAValidationResult with validation details
        """
        if not noa_number or not self.noa_db:
            return NOAValidationResult(
                noa_number=noa_number or "",
                is_valid=False,
                is_expired=False,
                message="NOA number not provided" if not noa_number else "NOA database not available"
            )

        # Normalize NOA number
        normalized = self._normalize_noa_number(noa_number)

        # Search database
        products = self.noa_db.search_products(approval_number=normalized)

        if not products:
            # Try partial match
            products = self.noa_db.search_products(approval_number=noa_number.split()[-1] if " " in noa_number else noa_number)

        if not products:
            return NOAValidationResult(
                noa_number=noa_number,
                is_valid=False,
                is_expired=False,
                message=f"NOA {noa_number} not found in database. Verify with Miami-Dade BCCO."
            )

        product = products[0]

        # Check expiration
        is_expired = False
        if product.get("expiration_date"):
            try:
                exp_date = datetime.strptime(product["expiration_date"], "%Y-%m-%d")
                is_expired = exp_date < datetime.now()
            except:
                pass

        return NOAValidationResult(
            noa_number=product.get("approval_number", noa_number),
            is_valid=not is_expired,
            is_expired=is_expired,
            product_name=product.get("product_name"),
            manufacturer=product.get("manufacturer_name"),
            expiration_date=product.get("expiration_date"),
            category=product.get("category"),
            design_pressure_positive=product.get("design_pressure_positive"),
            design_pressure_negative=product.get("design_pressure_negative"),
            missile_impact=product.get("missile_impact_level"),
            message="Valid and current" if not is_expired else f"EXPIRED on {product.get('expiration_date')}"
        )

    def _normalize_noa_number(self, noa_number: str) -> str:
        """Normalize NOA number format."""
        # Remove common prefixes
        normalized = re.sub(r'^(NOA\s*|#)', '', noa_number.strip(), flags=re.IGNORECASE)

        # Ensure consistent format: XX-XXXX.XX
        match = re.search(r'(\d{2})-?(\d{4})\.?(\d{2})?', normalized)
        if match:
            year = match.group(1)
            seq = match.group(2)
            rev = match.group(3) or "01"
            return f"NOA {year}-{seq}.{rev}"

        return noa_number.strip()

    def match_door_type(self, family_name: str, type_name: str,
                        min_design_pressure: float = None) -> NOAMatchResult:
        """
        Match a door type to NOA products.

        Args:
            family_name: Revit family name
            type_name: Revit type name
            min_design_pressure: Minimum required DP

        Returns:
            NOAMatchResult with matches and suggestions
        """
        return self._match_element_type(
            family_name=family_name,
            type_name=type_name,
            category="doors",
            min_design_pressure=min_design_pressure
        )

    def match_window_type(self, family_name: str, type_name: str,
                          min_design_pressure: float = None) -> NOAMatchResult:
        """
        Match a window type to NOA products.

        Args:
            family_name: Revit family name
            type_name: Revit type name
            min_design_pressure: Minimum required DP

        Returns:
            NOAMatchResult with matches and suggestions
        """
        return self._match_element_type(
            family_name=family_name,
            type_name=type_name,
            category="windows",
            min_design_pressure=min_design_pressure
        )

    def _match_element_type(
        self,
        family_name: str,
        type_name: str,
        category: str,
        min_design_pressure: float = None
    ) -> NOAMatchResult:
        """
        Match an element type to NOA products.

        Args:
            family_name: Revit family name
            type_name: Revit type name
            category: Product category
            min_design_pressure: Minimum required DP

        Returns:
            NOAMatchResult with matches
        """
        if not self.noa_db:
            return NOAMatchResult(
                element_mark="",
                element_type=f"{family_name}: {type_name}",
                category=category,
                provided_noa=None,
                validation=None,
                suggested_products=[],
                message="NOA database not available"
            )

        full_name = f"{family_name} {type_name}".lower()

        # Try to identify manufacturer
        manufacturer = self._identify_manufacturer(full_name)

        # Search for matching products
        search_kwargs = {"category": category, "large_missile_required": True}

        if manufacturer:
            search_kwargs["manufacturer"] = manufacturer

        if min_design_pressure:
            search_kwargs["min_design_pressure"] = min_design_pressure

        products = self.noa_db.search_products(**search_kwargs)

        # Build match list
        matches = []
        for product in products[:10]:  # Limit to top 10
            confidence = self._calculate_match_confidence(full_name, product)

            matches.append(NOAMatch(
                noa_number=product.get("approval_number", ""),
                product_name=product.get("product_name", ""),
                manufacturer=product.get("manufacturer_name", ""),
                confidence=confidence,
                category=product.get("category", ""),
                subcategory=product.get("subcategory"),
                design_pressure_positive=product.get("design_pressure_positive"),
                design_pressure_negative=product.get("design_pressure_negative"),
                missile_impact=product.get("missile_impact_level"),
                expiration_date=product.get("expiration_date"),
                match_reason=self._get_match_reason(full_name, product, confidence)
            ))

        # Sort by confidence
        confidence_order = {
            MatchConfidence.EXACT: 0,
            MatchConfidence.HIGH: 1,
            MatchConfidence.MEDIUM: 2,
            MatchConfidence.LOW: 3,
            MatchConfidence.NONE: 4
        }
        matches.sort(key=lambda m: confidence_order.get(m.confidence, 5))

        best_match = matches[0] if matches and matches[0].confidence != MatchConfidence.NONE else None

        return NOAMatchResult(
            element_mark="",
            element_type=f"{family_name}: {type_name}",
            category=category,
            provided_noa=None,
            validation=None,
            suggested_products=matches,
            best_match=best_match,
            needs_noa=True,
            message=f"Found {len(matches)} potential matches" if matches else "No matching products found"
        )

    def _identify_manufacturer(self, text: str) -> Optional[str]:
        """Identify manufacturer from text."""
        text_lower = text.lower()

        for canonical, aliases in self.MANUFACTURER_ALIASES.items():
            for alias in aliases:
                if alias in text_lower:
                    return canonical

        return None

    def _calculate_match_confidence(self, element_name: str, product: Dict) -> MatchConfidence:
        """Calculate confidence level of product match."""
        product_name = product.get("product_name", "").lower()
        manufacturer = product.get("manufacturer_name", "").lower()
        element_lower = element_name.lower()

        # Check for manufacturer match
        mfr_match = self._identify_manufacturer(manufacturer)
        element_mfr = self._identify_manufacturer(element_lower)

        has_mfr_match = mfr_match and element_mfr and mfr_match == element_mfr

        # Check for model/product name match
        name_words = set(re.findall(r'\w+', product_name))
        element_words = set(re.findall(r'\w+', element_lower))
        common_words = name_words & element_words
        name_match_ratio = len(common_words) / max(len(name_words), 1)

        # Calculate confidence
        if has_mfr_match and name_match_ratio > 0.5:
            return MatchConfidence.HIGH
        elif has_mfr_match or name_match_ratio > 0.3:
            return MatchConfidence.MEDIUM
        elif name_match_ratio > 0.1:
            return MatchConfidence.LOW
        else:
            return MatchConfidence.NONE

    def _get_match_reason(self, element_name: str, product: Dict,
                          confidence: MatchConfidence) -> str:
        """Get human-readable match reason."""
        if confidence == MatchConfidence.EXACT:
            return "Exact NOA number match"
        elif confidence == MatchConfidence.HIGH:
            return f"Strong match: {product.get('manufacturer_name')} product in same category"
        elif confidence == MatchConfidence.MEDIUM:
            return "Category and specification match"
        elif confidence == MatchConfidence.LOW:
            return "Same category only"
        else:
            return "No match - suggested based on category"

    def suggest_noa_products(
        self,
        element_data: Dict,
        category: str = None
    ) -> List[NOAMatch]:
        """
        Suggest NOA products for an element.

        Args:
            element_data: Element data dict with Type, Width, Height, etc.
            category: Product category (auto-detected if not provided)

        Returns:
            List of suggested NOAMatch products
        """
        if not self.noa_db:
            return []

        # Auto-detect category if not provided
        if not category:
            element_type = element_data.get("Type", "").lower()
            category = self._detect_category(element_type)

        if not category:
            return []

        # Build search criteria
        search_kwargs = {"category": category, "large_missile_required": True}

        # Get products
        products = self.noa_db.search_products(**search_kwargs)

        # Build match list
        matches = []
        for product in products[:10]:
            matches.append(NOAMatch(
                noa_number=product.get("approval_number", ""),
                product_name=product.get("product_name", ""),
                manufacturer=product.get("manufacturer_name", ""),
                confidence=MatchConfidence.LOW,
                category=product.get("category", ""),
                subcategory=product.get("subcategory"),
                design_pressure_positive=product.get("design_pressure_positive"),
                design_pressure_negative=product.get("design_pressure_negative"),
                missile_impact=product.get("missile_impact_level"),
                expiration_date=product.get("expiration_date"),
                match_reason="Suggested based on category"
            ))

        return matches

    def _detect_category(self, element_type: str) -> Optional[str]:
        """Detect product category from element type name."""
        element_lower = element_type.lower()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in element_lower:
                    return category

        return None

    def check_expiring_products(self, days: int = 90) -> List[NOAMatch]:
        """
        Get products expiring within specified days.

        Args:
            days: Number of days to check

        Returns:
            List of expiring products
        """
        if not self.noa_db:
            return []

        expiring = self.noa_db.check_expiring_approvals(days=days)

        return [
            NOAMatch(
                noa_number=p.get("approval_number", ""),
                product_name=p.get("product_name", ""),
                manufacturer=p.get("manufacturer_name", ""),
                confidence=MatchConfidence.EXACT,
                category=p.get("category", ""),
                expiration_date=p.get("expiration_date"),
                match_reason=f"Expires {p.get('expiration_date')}"
            )
            for p in expiring
        ]


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("NOA MATCHER TEST")
    print("=" * 70)

    matcher = NOAMatcher()

    # Test NOA validation
    print("\nTesting NOA Validation:")
    print("-" * 50)

    test_noas = [
        "NOA 21-0609.01",
        "NOA 20-1215.04",
        "NOA 99-9999.99",  # Invalid
        "21-0610.01",  # Without prefix
    ]

    for noa in test_noas:
        result = matcher.validate_noa_number(noa)
        status = "✓ Valid" if result.is_valid else ("⚠ Expired" if result.is_expired else "✗ Invalid")
        print(f"\n  {noa}:")
        print(f"    Status: {status}")
        if result.product_name:
            print(f"    Product: {result.product_name}")
            print(f"    Manufacturer: {result.manufacturer}")
        print(f"    Message: {result.message}")

    # Test door type matching
    print("\n" + "-" * 50)
    print("Testing Door Type Matching:")
    print("-" * 50)

    door_result = matcher.match_door_type("PGT", "WinGuard Sliding Glass Door")
    print(f"\n  Element: {door_result.element_type}")
    print(f"  Category: {door_result.category}")
    print(f"  Best Match: {door_result.best_match.noa_number if door_result.best_match else 'None'}")

    if door_result.suggested_products:
        print(f"\n  Suggested Products ({len(door_result.suggested_products)}):")
        for match in door_result.suggested_products[:3]:
            print(f"    [{match.confidence.value:6}] {match.noa_number}: {match.product_name}")
            print(f"             {match.match_reason}")

    # Test window type matching
    print("\n" + "-" * 50)
    print("Testing Window Type Matching:")
    print("-" * 50)

    window_result = matcher.match_window_type("CGI", "Sentinel Single Hung")
    print(f"\n  Element: {window_result.element_type}")
    print(f"  Best Match: {window_result.best_match.noa_number if window_result.best_match else 'None'}")

    if window_result.suggested_products:
        print(f"\n  Suggested Products:")
        for match in window_result.suggested_products[:3]:
            print(f"    [{match.confidence.value:6}] {match.noa_number}: {match.product_name}")

    # Test expiring products
    print("\n" + "-" * 50)
    print("Testing Expiring Products (180 days):")
    print("-" * 50)

    expiring = matcher.check_expiring_products(days=180)
    for product in expiring[:5]:
        print(f"  {product.noa_number}: {product.product_name}")
        print(f"    Expires: {product.expiration_date}")

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)
