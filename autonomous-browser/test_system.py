#!/usr/bin/env python3
"""
Test the Autonomous Browser System
Verifies all components work correctly
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


def test_vault():
    """Test credential vault"""
    print("\n1. Testing Credential Vault...")

    from vault.credentials import get_vault

    vault = get_vault()
    print("   ✓ Vault initialized")

    # Store test credential
    result = vault.store_credential(
        "test-site.example.com",
        "testuser@example.com",
        "testpassword123",
        "Test credential",
        True
    )
    print(f"   ✓ Credential stored: {result['status']}")

    # Retrieve credential
    cred = vault.get_credential("test-site.example.com")
    assert cred['status'] == 'success'
    assert cred['username'] == 'testuser@example.com'
    print(f"   ✓ Credential retrieved: {cred['username']}")

    # Delete test credential
    vault.delete_credential("test-site.example.com")
    print("   ✓ Test credential cleaned up")

    return True


def test_totp():
    """Test TOTP generation"""
    print("\n2. Testing TOTP Generator...")

    from vault.totp import generate_totp, verify_totp_seed

    # Standard test seed
    test_seed = "JBSWY3DPEHPK3PXP"

    # Verify seed
    result = verify_totp_seed(test_seed)
    assert result['status'] == 'valid'
    print(f"   ✓ TOTP seed valid")

    # Generate code
    code, remaining = generate_totp(test_seed)
    assert len(code) == 6
    assert code.isdigit()
    print(f"   ✓ TOTP code generated: {code} (valid for {remaining}s)")

    return True


def test_human_behavior():
    """Test human behavior simulation"""
    print("\n3. Testing Human Behavior Simulation...")

    from browser.human_behavior import HumanBehavior

    human = HumanBehavior()

    # Test typing delay variation
    delays = [human.typing_delay() for _ in range(10)]
    assert len(set(delays)) > 1, "Delays should vary"
    print(f"   ✓ Typing delays vary: {[f'{d:.3f}' for d in delays[:5]]}")

    # Test bezier curve generation
    curve = human.bezier_curve((0, 0), (100, 100), 10)
    assert len(curve) == 11
    print(f"   ✓ Bezier curve generated: {len(curve)} points")

    return True


def test_session_manager():
    """Test session persistence"""
    print("\n4. Testing Session Manager...")

    from browser.session_manager import get_session_manager

    sm = get_session_manager()

    # Save test session
    test_cookies = [
        {"name": "session", "value": "abc123", "domain": ".example.com"}
    ]
    result = sm.save_session("test.example.com", test_cookies)
    print(f"   ✓ Session saved: {result['status']}")

    # Retrieve session
    session = sm.get_session("test.example.com")
    assert session['status'] == 'success'
    print(f"   ✓ Session retrieved: {len(session['cookies'])} cookies")

    # Delete test session
    sm.delete_session("test.example.com")
    print("   ✓ Test session cleaned up")

    return True


def test_action_logger():
    """Test action logging"""
    print("\n5. Testing Action Logger...")

    from logger.action_logger import ActionLogger, LogBrowser

    logger = ActionLogger("test_session")

    # Log actions
    logger.log_action("navigate", {"url": "https://example.com"})
    logger.log_action("click", {"selector": "#button"})
    logger.log_credential_use("example.com", "user@test.com", "password")
    print("   ✓ Actions logged")

    # End session
    summary = logger.end_session("Test completed")
    assert summary['total_actions'] == 2
    print(f"   ✓ Session ended: {summary['total_actions']} actions, {summary['credentials_used']} cred uses")

    # Test log browser
    sessions = LogBrowser.list_sessions(days=1)
    assert len(sessions) > 0
    print(f"   ✓ Log browser working: {len(sessions)} recent sessions")

    return True


def test_imports():
    """Test all imports work"""
    print("\n6. Testing Module Imports...")

    try:
        from vault.credentials import CredentialVault, get_vault
        from vault.totp import generate_totp, get_totp_for_site
        from browser.stealth_browser import StealthBrowser
        from browser.human_behavior import HumanBehavior
        from browser.session_manager import SessionManager
        from logger.action_logger import ActionLogger, LogBrowser
        print("   ✓ All modules import successfully")
        return True
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        return False


def main():
    print("=" * 60)
    print("Autonomous Browser System Test")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Vault", test_vault),
        ("TOTP", test_totp),
        ("Human Behavior", test_human_behavior),
        ("Session Manager", test_session_manager),
        ("Action Logger", test_action_logger),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"   ✗ Error: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{len(results)} passed")

    if failed == 0:
        print("\n✓ All tests passed! System is ready to use.")
    else:
        print(f"\n✗ {failed} test(s) failed. Check the errors above.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
