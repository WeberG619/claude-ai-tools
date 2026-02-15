#!/usr/bin/env python3
"""
Credential Vault Manager CLI
Manage stored credentials and TOTP seeds

Usage:
    python manage_vault.py list                    - List all credentials
    python manage_vault.py add <site>              - Add credential (interactive)
    python manage_vault.py delete <site>           - Delete credential
    python manage_vault.py totp-add <site>         - Add TOTP seed (interactive)
    python manage_vault.py totp-code <site>        - Generate TOTP code
    python manage_vault.py sessions                - List saved sessions
"""

import sys
import getpass
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from vault.credentials import get_vault
from vault.totp import generate_totp, get_totp_for_site


def cmd_list():
    """List all credentials"""
    vault = get_vault()
    creds = vault.list_credentials()

    if not creds:
        print("No credentials stored.")
        return

    print(f"\n{'Site':<30} {'Username':<30} {'Auto-Login':<12} {'Uses':<6}")
    print("-" * 80)
    for c in creds:
        print(f"{c['site']:<30} {c['username']:<30} {str(c['auto_login']):<12} {c['use_count']:<6}")
    print()


def cmd_add(site: str):
    """Add a credential"""
    print(f"\nAdding credential for: {site}")
    username = input("Username/Email: ")
    password = getpass.getpass("Password: ")
    notes = input("Notes (optional): ")
    auto_login = input("Allow Claude to use without asking? (Y/n): ").lower() != 'n'

    vault = get_vault()
    result = vault.store_credential(site, username, password, notes, auto_login)
    print(f"\n✓ Credential stored for {site}")


def cmd_delete(site: str):
    """Delete a credential"""
    vault = get_vault()
    result = vault.delete_credential(site)
    if result['status'] == 'deleted':
        print(f"✓ Deleted credential for {site}")
    else:
        print(f"✗ No credential found for {site}")


def cmd_totp_add(site: str):
    """Add TOTP seed"""
    print(f"\nAdding TOTP for: {site}")
    print("Enter your TOTP secret (the code you'd normally put in Google Authenticator):")
    seed = input("TOTP Seed: ").strip()
    auto_generate = input("Allow Claude to generate codes without asking? (Y/n): ").lower() != 'n'

    vault = get_vault()

    # Verify the seed first
    from vault.totp import verify_totp_seed
    check = verify_totp_seed(seed)
    if check['status'] != 'valid':
        print(f"✗ Invalid TOTP seed: {check.get('error', 'Unknown error')}")
        return

    print(f"Test code generated: {check['test_code']} (verify this matches your authenticator)")
    confirm = input("Does this code match? (y/N): ").lower() == 'y'

    if confirm:
        result = vault.store_totp_seed(site, seed, auto_generate)
        print(f"✓ TOTP stored for {site}")
    else:
        print("✗ TOTP not stored (code didn't match)")


def cmd_totp_code(site: str):
    """Generate TOTP code"""
    result = get_totp_for_site(site)
    if result['status'] == 'success':
        print(f"\n  Site: {result['site']}")
        print(f"  Code: {result['code']}")
        print(f"  Valid for: {result['seconds_remaining']} seconds")
    else:
        print(f"✗ {result.get('message', 'No TOTP configured for this site')}")


def cmd_sessions():
    """List saved sessions"""
    from browser.session_manager import get_session_manager
    sm = get_session_manager()
    sessions = sm.list_sessions()

    if not sessions:
        print("No sessions saved.")
        return

    print(f"\n{'Site':<30} {'Cookies':<10} {'Saved':<20}")
    print("-" * 65)
    for s in sessions:
        print(f"{s['site']:<30} {s['cookie_count']:<10} {s['saved_at'][:19]}")
    print()


def cmd_totp_list():
    """List TOTP sites"""
    vault = get_vault()
    sites = vault.list_totp_sites()

    if not sites:
        print("No TOTP seeds stored.")
        return

    print(f"\n{'Site':<30} {'Auto-Generate':<15}")
    print("-" * 50)
    for s in sites:
        print(f"{s['site']:<30} {str(s['auto_generate']):<15}")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == 'list':
        cmd_list()
    elif cmd == 'add' and len(sys.argv) >= 3:
        cmd_add(sys.argv[2])
    elif cmd == 'delete' and len(sys.argv) >= 3:
        cmd_delete(sys.argv[2])
    elif cmd == 'totp-add' and len(sys.argv) >= 3:
        cmd_totp_add(sys.argv[2])
    elif cmd == 'totp-code' and len(sys.argv) >= 3:
        cmd_totp_code(sys.argv[2])
    elif cmd == 'totp-list':
        cmd_totp_list()
    elif cmd == 'sessions':
        cmd_sessions()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
