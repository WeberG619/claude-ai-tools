#!/usr/bin/env python3
"""
Quick test script for Weber SDK.

Run this to verify the SDK is working:
    python test_sdk.py
"""

import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/weber-sdk")

def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    from weber_sdk import Weber
    from weber_sdk import discover_servers, MCPServerConfig
    from weber_sdk.exceptions import (
        WeberSDKError,
        ConnectionError,
        ServerNotFoundError,
        ToolNotFoundError,
        ToolExecutionError,
    )
    from weber_sdk.services import (
        BaseService,
        VoiceService,
        ExcelService,
        RevitService,
        GenericService,
    )
    from weber_sdk.transports import StdioTransport, BaseTransport
    print("  All imports successful!")


def test_discovery():
    """Test server discovery."""
    print("\nTesting server discovery...")
    from weber_sdk import discover_servers

    servers = discover_servers(include_disabled=True)
    print(f"  Found {len(servers)} servers:")
    for name, config in sorted(servers.items()):
        status = "DISABLED" if config.disabled else "enabled"
        print(f"    - {name} ({status})")


def test_client_init():
    """Test client initialization."""
    print("\nTesting client initialization...")
    from weber_sdk import Weber

    w = Weber()
    servers = w.list_servers()
    print(f"  Client initialized with {len(servers)} servers")

    # Test property access
    _ = w.voice
    _ = w.excel
    print("  Service proxies created successfully")


def test_server_info():
    """Test getting server info."""
    print("\nTesting server info...")
    from weber_sdk import Weber

    w = Weber()
    servers = w.list_servers()

    if servers:
        first = servers[0]
        info = w.get_server_info(first)
        print(f"  Server '{first}' info:")
        print(f"    Command: {info.get('command')}")
        print(f"    Args: {info.get('args', [])[:2]}...")


def test_categories():
    """Test server categorization."""
    print("\nTesting server categories...")
    from weber_sdk.discovery import list_server_categories

    categories = list_server_categories()
    print("  Categories found:")
    for cat, servers in categories.items():
        print(f"    {cat}: {servers}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Weber SDK Quick Test")
    print("=" * 60)

    try:
        test_imports()
        test_discovery()
        test_client_init()
        test_server_info()
        test_categories()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
