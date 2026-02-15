"""
Founder's Companion - The Vault
===============================
Secure, encrypted storage for founders' private confessions.
Zero-knowledge architecture - only the founder can decrypt their entries.
"""

import os
import base64
import hashlib
from datetime import datetime
from typing import Optional, List
from dataclasses import asdict

# Cryptography for secure encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not installed. Vault encryption disabled.")

from models import VaultEntry, MoodLevel, ChallengeCategory, Founder
from config import get_config


class VaultEncryption:
    """Handles encryption/decryption for vault entries."""

    def __init__(self, founder_id: str, user_passphrase: str):
        """
        Initialize encryption with founder-specific key.

        The key is derived from:
        1. Founder's unique ID (salt)
        2. User's passphrase (only they know)

        This means even we cannot decrypt their entries.
        """
        self.founder_id = founder_id

        if CRYPTO_AVAILABLE:
            # Derive key from passphrase + founder_id as salt
            salt = hashlib.sha256(founder_id.encode()).digest()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )

            key = base64.urlsafe_b64encode(kdf.derive(user_passphrase.encode()))
            self.cipher = Fernet(key)
        else:
            self.cipher = None

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a vault entry."""
        if self.cipher:
            return self.cipher.encrypt(plaintext.encode())
        else:
            # Fallback: base64 encode (NOT SECURE - for demo only)
            return base64.b64encode(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt a vault entry."""
        if self.cipher:
            return self.cipher.decrypt(ciphertext).decode()
        else:
            # Fallback: base64 decode
            return base64.b64decode(ciphertext).decode()


class Vault:
    """
    The Vault - A safe space for founders to express their fears.

    Key principles:
    1. PRIVACY: Content is encrypted with founder's passphrase
    2. NO JUDGMENT: AI responds with empathy, not advice
    3. PATTERN RECOGNITION: We track mood, not content
    4. SAFETY: Crisis detection triggers appropriate resources
    """

    # Crisis keywords that trigger safety protocols
    CRISIS_KEYWORDS = [
        "suicide", "kill myself", "end it all", "not worth living",
        "hurt myself", "self harm", "no way out", "give up on life"
    ]

    # Safety resources
    CRISIS_RESOURCES = """
    You're not alone. Please reach out for support:

    🆘 National Suicide Prevention Lifeline: 988 (US)
    🆘 Crisis Text Line: Text HOME to 741741
    🆘 International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/

    Your life matters. Your struggles are real, but temporary.
    Help is available 24/7.
    """

    def __init__(self, database):
        self.db = database
        self.config = get_config()

    def create_entry(
        self,
        founder: Founder,
        content: str,
        mood_before: MoodLevel,
        passphrase: str,
        challenge: Optional[ChallengeCategory] = None
    ) -> VaultEntry:
        """
        Create a new vault entry.

        The content is immediately encrypted and the plaintext is discarded.
        """
        # Check for crisis content BEFORE encrypting
        is_crisis = self._detect_crisis(content)

        # Create encryption handler
        encryption = VaultEncryption(founder.id, passphrase)

        # Create entry
        entry = VaultEntry(
            founder_id=founder.id,
            content="[ENCRYPTED]",  # Never store plaintext
            encrypted_content=encryption.encrypt(content),
            mood_before=mood_before,
            challenge_category=challenge,
        )

        # Generate AI response
        entry.ai_response = self._generate_response(
            content, mood_before, challenge, is_crisis
        )

        # Save to database (content is encrypted)
        self.db.save_vault_entry(entry)

        return entry

    def read_entry(
        self,
        entry_id: str,
        founder: Founder,
        passphrase: str
    ) -> Optional[VaultEntry]:
        """
        Read and decrypt a vault entry.

        Only the founder with correct passphrase can read.
        """
        entry = self.db.get_vault_entry(entry_id)

        if not entry or entry.founder_id != founder.id:
            return None

        # Decrypt content
        encryption = VaultEncryption(founder.id, passphrase)
        try:
            entry.content = encryption.decrypt(entry.encrypted_content)
            return entry
        except Exception:
            # Wrong passphrase
            return None

    def _detect_crisis(self, content: str) -> bool:
        """Check if content indicates crisis that needs immediate support."""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.CRISIS_KEYWORDS)

    def _generate_response(
        self,
        content: str,
        mood: MoodLevel,
        challenge: Optional[ChallengeCategory],
        is_crisis: bool
    ) -> str:
        """
        Generate an empathetic AI response.

        For MVP, we use template responses. Production would use GPT-4.
        """
        if is_crisis:
            return self._crisis_response()

        # Template responses based on mood and challenge
        if mood.value <= 2:  # Crisis or Struggling
            return self._struggling_response(challenge)
        elif mood.value <= 4:  # Difficult or Okay
            return self._supportive_response(challenge)
        else:  # Good or Thriving
            return self._celebrating_response(challenge)

    def _crisis_response(self) -> str:
        """Response for crisis situations."""
        return f"""
I hear you, and I'm glad you're sharing this with me.

What you're feeling is incredibly heavy, and it takes courage to express it.
You don't have to carry this alone.

{self.CRISIS_RESOURCES}

I'm here whenever you need to talk. But please also reach out to someone
who can provide immediate support. You matter more than you know.

💙
"""

    def _struggling_response(self, challenge: Optional[ChallengeCategory]) -> str:
        """Response for struggling founders."""
        challenge_specific = ""
        if challenge == ChallengeCategory.FUNDRAISING:
            challenge_specific = "Fundraising is brutal. Every 'no' feels personal, but it's not. The right investor is out there."
        elif challenge == ChallengeCategory.BURNOUT:
            challenge_specific = "Burnout isn't weakness - it's your body telling you something important. Rest is not optional."
        elif challenge == ChallengeCategory.LONELINESS:
            challenge_specific = "The loneliness of leadership is real. You're not the only one feeling this way."
        elif challenge == ChallengeCategory.IMPOSTER_SYNDROME:
            challenge_specific = "Imposter syndrome hits the best founders. It means you care deeply about doing this right."

        return f"""
Thank you for trusting me with this. What you're feeling is valid.

{challenge_specific}

Here's what I want you to know:
• This feeling is temporary, even when it doesn't feel that way
• 72% of founders go through exactly what you're experiencing
• Struggling doesn't mean failing - it means you're in the arena

One small thing you could do right now: Take three deep breaths.
Then do one tiny task. Just one. That's enough for now.

I'm here whenever you need to come back. This vault is always open.

💙
"""

    def _supportive_response(self, challenge: Optional[ChallengeCategory]) -> str:
        """Response for founders who are managing but challenged."""
        return """
I appreciate you sharing this with me.

It sounds like you're navigating some real challenges, but you're
still showing up. That takes strength.

A few thoughts:
• Progress isn't always visible day-to-day, but it compounds
• The fact that you're reflecting on this shows self-awareness
• You're allowed to have hard days - they don't define your journey

What's one small win you can acknowledge from this week?
Sometimes we need to remind ourselves how far we've come.

Keep going. I believe in you.

💙
"""

    def _celebrating_response(self, challenge: Optional[ChallengeCategory]) -> str:
        """Response for founders doing well."""
        return """
I love hearing this energy from you!

It's important to pause and acknowledge when things are going well.
Founders often forget to celebrate their wins.

Savor this moment. You've earned it.

And remember - when harder days come (they will), you can look back
at entries like this one. You've proven you can get here.

What made today good? Hold onto that.

🌟
"""

    def get_mood_history(self, founder: Founder, days: int = 30) -> List[dict]:
        """Get mood trends without revealing content."""
        entries = self.db.get_vault_entries_by_founder(
            founder.id,
            limit=100,
            days=days
        )

        return [
            {
                "date": e.timestamp.isoformat(),
                "mood_before": e.mood_before.value,
                "mood_after": e.mood_after.value if e.mood_after else None,
                "challenge": e.challenge_category.value if e.challenge_category else None,
                "response_helpful": e.response_helpful
            }
            for e in entries
        ]

    def update_response_helpful(
        self,
        entry_id: str,
        founder: Founder,
        helpful: bool
    ) -> bool:
        """Let founder rate if AI response was helpful."""
        entry = self.db.get_vault_entry(entry_id)
        if entry and entry.founder_id == founder.id:
            entry.response_helpful = helpful
            self.db.update_vault_entry(entry)
            return True
        return False

    def set_mood_after(
        self,
        entry_id: str,
        founder: Founder,
        mood_after: MoodLevel
    ) -> bool:
        """Record mood after using vault (did it help?)."""
        entry = self.db.get_vault_entry(entry_id)
        if entry and entry.founder_id == founder.id:
            entry.mood_after = mood_after
            self.db.update_vault_entry(entry)
            return True
        return False
