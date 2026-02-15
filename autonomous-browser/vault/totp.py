"""
TOTP Code Generator
Generates time-based one-time passwords for 2FA
"""

import hmac
import hashlib
import struct
import time
import base64
from typing import Tuple

from .credentials import get_vault


def generate_totp(seed: str, time_step: int = 30, digits: int = 6) -> Tuple[str, int]:
    """
    Generate TOTP code from seed.

    Args:
        seed: Base32 encoded secret
        time_step: Time step in seconds (usually 30)
        digits: Number of digits in code (usually 6)

    Returns:
        Tuple of (code, seconds_remaining)
    """
    # Clean and decode the seed
    seed = seed.replace(" ", "").upper()

    # Add padding if needed
    padding = 8 - (len(seed) % 8)
    if padding != 8:
        seed += "=" * padding

    try:
        key = base64.b32decode(seed)
    except Exception as e:
        raise ValueError(f"Invalid TOTP seed: {e}")

    # Get current time counter
    current_time = int(time.time())
    counter = current_time // time_step

    # Calculate seconds remaining
    seconds_remaining = time_step - (current_time % time_step)

    # Generate HMAC-SHA1
    counter_bytes = struct.pack(">Q", counter)
    hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()

    # Dynamic truncation
    offset = hmac_hash[-1] & 0x0F
    truncated = struct.unpack(">I", hmac_hash[offset:offset + 4])[0]
    truncated &= 0x7FFFFFFF

    # Generate code
    code = truncated % (10 ** digits)
    code_str = str(code).zfill(digits)

    return code_str, seconds_remaining


def get_totp_for_site(site: str, require_approval: bool = False) -> dict:
    """
    Get TOTP code for a specific site.

    Args:
        site: Website domain
        require_approval: If True, always asks for manual approval

    Returns:
        Dict with code and metadata
    """
    vault = get_vault()
    seed_data = vault.get_totp_seed(site)

    if seed_data["status"] != "success":
        return seed_data

    # Check if manual approval needed
    if require_approval or not seed_data.get("auto_generate", True):
        return {
            "status": "approval_required",
            "site": site,
            "message": f"Manual approval required to generate TOTP for {site}"
        }

    try:
        code, seconds_remaining = generate_totp(seed_data["seed"])
        return {
            "status": "success",
            "site": site,
            "code": code,
            "seconds_remaining": seconds_remaining,
            "message": f"Code valid for {seconds_remaining} more seconds"
        }
    except Exception as e:
        return {
            "status": "error",
            "site": site,
            "error": str(e)
        }


def verify_totp_seed(seed: str) -> dict:
    """
    Verify a TOTP seed is valid by generating a test code.

    Args:
        seed: Base32 encoded secret to verify

    Returns:
        Dict with validation result
    """
    try:
        code, remaining = generate_totp(seed)
        return {
            "status": "valid",
            "test_code": code,
            "seconds_remaining": remaining
        }
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e)
        }


if __name__ == "__main__":
    # Test with a sample seed
    test_seed = "JBSWY3DPEHPK3PXP"  # Standard test seed
    code, remaining = generate_totp(test_seed)
    print(f"Test TOTP Code: {code}")
    print(f"Valid for: {remaining} seconds")
