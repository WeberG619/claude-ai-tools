"""
Secure Credential Vault for Autonomous Browser
Encrypts and stores passwords, TOTP seeds, and session tokens
"""

import json
import os
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VAULT_DIR = Path(__file__).parent
VAULT_FILE = VAULT_DIR / "vault.enc"
SALT_FILE = VAULT_DIR / ".salt"


class CredentialVault:
    """Encrypted credential storage"""

    def __init__(self, master_password: str = None):
        """
        Initialize vault with master password.
        If no password provided, uses machine-specific key.
        """
        self.master_password = master_password or self._get_machine_key()
        self._fernet = self._create_fernet()
        self._vault_data = self._load_vault()

    def _get_machine_key(self) -> str:
        """Generate machine-specific key (fallback if no master password)"""
        import platform
        try:
            username = os.getlogin()
        except OSError:
            # Fallback for WSL or environments where getlogin() fails
            username = os.environ.get('USER', os.environ.get('USERNAME', 'default'))
        machine_id = f"{platform.node()}-{username}-weber-autonomous"
        return hashlib.sha256(machine_id.encode()).hexdigest()

    def _get_or_create_salt(self) -> bytes:
        """Get or create salt for key derivation"""
        if SALT_FILE.exists():
            return SALT_FILE.read_bytes()
        salt = os.urandom(16)
        SALT_FILE.write_bytes(salt)
        return salt

    def _create_fernet(self) -> Fernet:
        """Create Fernet cipher from master password"""
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_password.encode())
        )
        return Fernet(key)

    def _load_vault(self) -> dict:
        """Load and decrypt vault data"""
        if not VAULT_FILE.exists():
            return {
                "credentials": {},
                "totp_seeds": {},
                "cookies": {},
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }

        encrypted_data = VAULT_FILE.read_bytes()
        decrypted = self._fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode())

    def _save_vault(self):
        """Encrypt and save vault data"""
        self._vault_data["metadata"]["last_modified"] = datetime.now().isoformat()
        json_data = json.dumps(self._vault_data, indent=2)
        encrypted = self._fernet.encrypt(json_data.encode())
        VAULT_FILE.write_bytes(encrypted)

    # ==================== Credential Management ====================

    def store_credential(self, site: str, username: str, password: str,
                        notes: str = "", auto_login: bool = True) -> dict:
        """
        Store a credential for a website.

        Args:
            site: Website domain (e.g., 'github.com')
            username: Login username/email
            password: Login password
            notes: Optional notes
            auto_login: If True, Claude can use without asking
        """
        self._vault_data["credentials"][site] = {
            "username": username,
            "password": password,
            "notes": notes,
            "auto_login": auto_login,
            "created": datetime.now().isoformat(),
            "last_used": None,
            "use_count": 0
        }
        self._save_vault()
        return {"status": "stored", "site": site, "username": username}

    def get_credential(self, site: str, require_approval: bool = False) -> dict:
        """
        Retrieve credential for a site.

        Args:
            site: Website domain
            require_approval: If True, always asks user even if auto_login is True
        """
        # Try exact match first
        cred = self._vault_data["credentials"].get(site)

        # Try partial match if no exact match
        if not cred:
            for stored_site, stored_cred in self._vault_data["credentials"].items():
                if site in stored_site or stored_site in site:
                    cred = stored_cred
                    site = stored_site
                    break

        if not cred:
            return {"status": "not_found", "site": site}

        # Check if manual approval needed
        if require_approval or not cred.get("auto_login", True):
            return {
                "status": "approval_required",
                "site": site,
                "username": cred["username"],
                "message": f"Manual approval required to use credentials for {site}"
            }

        # Update usage stats
        cred["last_used"] = datetime.now().isoformat()
        cred["use_count"] = cred.get("use_count", 0) + 1
        self._save_vault()

        return {
            "status": "success",
            "site": site,
            "username": cred["username"],
            "password": cred["password"]
        }

    def list_credentials(self) -> list:
        """List all stored credentials (without passwords)"""
        return [
            {
                "site": site,
                "username": cred["username"],
                "auto_login": cred.get("auto_login", True),
                "last_used": cred.get("last_used"),
                "use_count": cred.get("use_count", 0)
            }
            for site, cred in self._vault_data["credentials"].items()
        ]

    def delete_credential(self, site: str) -> dict:
        """Delete a stored credential"""
        if site in self._vault_data["credentials"]:
            del self._vault_data["credentials"][site]
            self._save_vault()
            return {"status": "deleted", "site": site}
        return {"status": "not_found", "site": site}

    def update_auto_login(self, site: str, auto_login: bool) -> dict:
        """Update auto_login setting for a credential"""
        if site in self._vault_data["credentials"]:
            self._vault_data["credentials"][site]["auto_login"] = auto_login
            self._save_vault()
            return {"status": "updated", "site": site, "auto_login": auto_login}
        return {"status": "not_found", "site": site}

    # ==================== TOTP Management ====================

    def store_totp_seed(self, site: str, seed: str,
                       auto_generate: bool = True) -> dict:
        """
        Store TOTP seed for 2FA.

        Args:
            site: Website domain
            seed: TOTP secret seed (base32 encoded)
            auto_generate: If True, Claude can generate codes without asking
        """
        # Clean the seed (remove spaces, uppercase)
        seed = seed.replace(" ", "").upper()

        self._vault_data["totp_seeds"][site] = {
            "seed": seed,
            "auto_generate": auto_generate,
            "created": datetime.now().isoformat(),
            "last_used": None
        }
        self._save_vault()
        return {"status": "stored", "site": site}

    def get_totp_seed(self, site: str) -> dict:
        """Get TOTP seed (for code generation)"""
        totp = self._vault_data["totp_seeds"].get(site)
        if not totp:
            # Try partial match
            for stored_site, stored_totp in self._vault_data["totp_seeds"].items():
                if site in stored_site or stored_site in site:
                    totp = stored_totp
                    site = stored_site
                    break

        if not totp:
            return {"status": "not_found", "site": site}

        return {
            "status": "success",
            "site": site,
            "seed": totp["seed"],
            "auto_generate": totp.get("auto_generate", True)
        }

    def list_totp_sites(self) -> list:
        """List sites with TOTP configured"""
        return [
            {
                "site": site,
                "auto_generate": totp.get("auto_generate", True),
                "last_used": totp.get("last_used")
            }
            for site, totp in self._vault_data["totp_seeds"].items()
        ]

    # ==================== Cookie/Session Management ====================

    def store_cookies(self, site: str, cookies: list) -> dict:
        """Store browser cookies for session persistence"""
        self._vault_data["cookies"][site] = {
            "cookies": cookies,
            "stored": datetime.now().isoformat()
        }
        self._save_vault()
        return {"status": "stored", "site": site, "cookie_count": len(cookies)}

    def get_cookies(self, site: str) -> dict:
        """Retrieve stored cookies for a site"""
        cookie_data = self._vault_data["cookies"].get(site)
        if not cookie_data:
            return {"status": "not_found", "site": site}
        return {
            "status": "success",
            "site": site,
            "cookies": cookie_data["cookies"],
            "stored": cookie_data["stored"]
        }

    def clear_cookies(self, site: str = None) -> dict:
        """Clear cookies for a site or all sites"""
        if site:
            if site in self._vault_data["cookies"]:
                del self._vault_data["cookies"][site]
                self._save_vault()
                return {"status": "cleared", "site": site}
            return {"status": "not_found", "site": site}
        else:
            count = len(self._vault_data["cookies"])
            self._vault_data["cookies"] = {}
            self._save_vault()
            return {"status": "cleared_all", "count": count}


# Singleton instance
_vault_instance = None

def get_vault(master_password: str = None) -> CredentialVault:
    """Get or create vault instance"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = CredentialVault(master_password)
    return _vault_instance


if __name__ == "__main__":
    # Test the vault
    vault = get_vault()
    print("Vault initialized successfully")
    print(f"Stored credentials: {len(vault.list_credentials())}")
    print(f"TOTP sites: {len(vault.list_totp_sites())}")
