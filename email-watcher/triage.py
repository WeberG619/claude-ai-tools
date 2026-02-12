"""
Email Triage Module - Pattern-based email classification.

Classifies emails into categories:
- urgent_response: Needs immediate attention (client emails, deadlines)
- needs_response: Should respond but not urgent
- fyi: Informational only (newsletters, notifications)
- spam: Marketing, unsubscribe candidates

No AI/Ollama dependency - pure pattern matching for speed and reliability.
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# PATTERN CONFIGURATION
# ============================================================================

# Known sender patterns (checked against full "From" field including name)
SENDER_PATTERNS = {
    "urgent_response": [
        # Your clients - ADD MORE AS NEEDED
        r".*@bdarchitect\.net",      # BD Architect team
        r".*@lesfantal\.com",        # Fantal Consulting
        r".*@afuriaesthetics\.com",  # Afuri client
        r".*@ara-engineering\.com",  # ARA Engineering
        r".*@bartholemewpartners\.com",  # Bartholemew Partners
        r".*permit.*@.*\.gov",       # Government permits
        r".*inspection.*@.*\.gov",   # Government inspections
    ],
    "fyi": [
        # === NOREPLY/AUTOMATED SENDERS (username patterns) ===
        r".*noreply@",               # noreply@anything
        r".*no-reply@",              # no-reply@anything
        r".*donotreply@",            # donotreply@anything
        r".*do-not-reply@",          # do-not-reply@anything
        r".*notifications?@",        # notification@ or notifications@
        r".*notify@",                # notify@anything
        r".*alert@",                 # alert@anything
        r".*alerts@",                # alerts@anything
        r".*news@",                  # news@anything
        r".*newsletter@",            # newsletter@anything
        r".*digest@",                # digest@anything
        r".*updates?@",              # update@ or updates@
        r".*info@",                  # info@anything (usually automated)
        r".*hello@",                 # hello@ (usually marketing)
        r".*support@",               # support@ (usually automated)
        r".*team@",                  # team@ (usually marketing)

        # === SUBDOMAIN PATTERNS (marketing/engagement subdomains) ===
        r".*@e\.",                   # e.company.com (email marketing)
        r".*@m\.",                   # m.company.com (mobile/marketing)
        r".*@mail\.",                # mail.company.com
        r".*@email\.",               # email.company.com
        r".*@news\.",                # news.company.com
        r".*@info\.",                # info.company.com
        r".*@updates\.",             # updates.company.com
        r".*@engage\.",              # engage.company.com
        r".*@engagement\.",          # engagement.company.com
        r".*@notifications?\.",      # notification(s).company.com
        r".*@campaigns?\.",          # campaign(s).company.com
        r".*@promo\.",               # promo.company.com

        # === EMAIL SERVICE PROVIDERS (bulk senders) ===
        r".*@.*\.ccsend\.com",       # Constant Contact
        r".*@.*\.mailchimp\.com",    # Mailchimp
        r".*@.*\.sendgrid\.net",     # SendGrid
        r".*@.*\.amazonses\.com",    # Amazon SES
        r".*@.*\.hubspotemail\.net", # HubSpot
        r".*@.*\.klaviyo\.com",      # Klaviyo
        r".*@.*\.mailgun\.org",      # Mailgun
        r".*@.*\.postmarkapp\.com",  # Postmark
        r".*@.*\.intercom-mail\.com",# Intercom
        r".*@.*\.zendesk\.com",      # Zendesk
        r".*@.*\.freshdesk\.com",    # Freshdesk

        # === SOCIAL MEDIA ===
        r".*@linkedin\.com",
        r".*@facebookmail\.com",
        r".*@twitter\.com",
        r".*@x\.com",
        r".*@instagram\.com",
        r".*@pinterest\.com",
        r".*@tiktok\.com",
        r".*@youtube\.com",
        r".*@reddit\.com",

        # === COMMON SERVICES (usually FYI) ===
        r".*@.*stripe\.com",
        r".*@.*paypal\.com",
        r".*@.*square\.com",
        r".*@.*uber\.com",
        r".*@.*lyft\.com",
        r".*@.*doordash\.com",
        r".*@.*grubhub\.com",
        r".*@.*ubereats\.com",
        r".*@.*zoom\.us",
        r".*@.*zoom\.com",
        r".*@.*microsoft\.com",
        r".*@.*google\.com",
        r".*@.*apple\.com",
        r".*@.*amazon\.com",
        r".*@.*aws\.amazon\.com",
        r".*@.*github\.com",
        r".*@.*gitlab\.com",
        r".*@.*bitbucket\.org",
        r".*@.*heroku\.com",
        r".*@.*vercel\.com",
        r".*@.*netlify\.com",
        r".*@.*railway\.app",
        r".*@.*ngrok\.com",
        r".*@.*digitalocean\.com",
        r".*@.*cloudflare\.com",
        r".*@.*dropbox\.com",
        r".*@.*slack\.com",
        r".*@.*notion\.so",
        r".*@.*asana\.com",
        r".*@.*trello\.com",
        r".*@.*monday\.com",
        r".*@.*figma\.com",
        r".*@.*canva\.com",
        r".*@.*adobe\.com",
        r".*@.*autodesk\.com",
        r".*@.*anthropic\.com",
        r".*@.*openai\.com",
        r".*@.*resend\.com",
        r".*@.*wispr\.ai",
        r".*@.*coinbase\.com",
        r".*@.*robinhood\.com",
        r".*@.*fidelity\.com",
        r".*@.*vanguard\.com",
        r".*@.*schwab\.com",

        # === TECH/SAAS/AI COMPANIES ===
        r".*@.*heygen\.com",
        r".*@.*jetbrains\.com",
        r".*@.*augmentcode\.com",
        r".*@.*cursor\.com",
        r".*@.*cursor\.sh",
        r".*@.*replit\.com",
        r".*@.*supabase\.com",
        r".*@.*supabase\.io",
        r".*@.*railway\.app",
        r".*@.*fly\.io",
        r".*@.*render\.com",
        r".*@.*planetscale\.com",
        r".*@.*turso\.tech",
        r".*@.*neon\.tech",
        r".*@.*convex\.dev",
        r".*@.*clerk\.com",
        r".*@.*clerk\.dev",
        r".*@.*auth0\.com",
        r".*@.*twilio\.com",
        r".*@.*sendbird\.com",
        r".*@.*loom\.com",
        r".*@.*miro\.com",
        r".*@.*airtable\.com",
        r".*@.*zapier\.com",
        r".*@.*make\.com",
        r".*@.*n8n\.io",
        r".*@.*hubspot\.com",
        r".*@.*salesforce\.com",
        r".*@.*intercom\.com",
        r".*@.*crisp\.chat",
        r".*@.*grammarly\.com",
        r".*@.*notion\.com",
        r".*@.*coda\.io",
        r".*@.*linear\.app",
        r".*@.*descript\.com",
        r".*@.*midjourney\.com",
        r".*@.*stability\.ai",
        r".*@.*runway\.com",
        r".*@.*runwayml\.com",
        r".*@.*elevenlabs\.io",
        r".*@.*synthesia\.io",
        r".*@.*jasper\.ai",
        r".*@.*copy\.ai",
        r".*@.*writesonic\.com",
        r".*@.*perplexity\.ai",
        r".*@.*huggingface\.co",
        r".*@.*cohere\.com",
        r".*@.*mistral\.ai",
        r".*@.*together\.ai",
        r".*@.*anyscale\.com",
        r".*@.*weights\.com",
        r".*@.*wandb\.com",
        r".*@.*datadog\.com",
        r".*@.*sentry\.io",
        r".*@.*launchdarkly\.com",
        r".*@.*postman\.com",
        r".*@.*insomnia\.rest",
        r".*@.*docker\.com",
        r".*@.*hashicorp\.com",
        r".*@.*terraform\.io",
        r".*@.*pulumi\.com",
        r".*@.*snyk\.io",
        r".*@.*sonarqube\.com",
        r".*@.*circleci\.com",
        r".*@.*travis-ci\.com",
        r".*@.*buildkite\.com",
        r".*@.*semaphoreci\.com",
        r".*@.*gumroad\.com",
        r".*@.*lemonsqueezy\.com",
        r".*@.*paddle\.com",
        r".*@.*producthunt\.com",
        r".*@.*indiehackers\.com",

        # === RETAIL/COMMERCE ===
        r".*@.*walmart\.com",
        r".*@.*target\.com",
        r".*@.*bestbuy\.com",
        r".*@.*homedepot\.com",
        r".*@.*lowes\.com",
        r".*@.*costco\.com",
        r".*@.*samsclub\.com",
        r".*@.*ebay\.com",
        r".*@.*etsy\.com",
        r".*@.*wayfair\.com",
        r".*@.*ikea\.com",
    ],
    "spam": [
        # Explicit marketing domains/patterns
        r".*@marketing\.",
        r".*@promo\.",
        r".*@deals\.",
        r".*@offers\.",
        r".*@sale\.",
        r".*@discount\.",
        r".*promo.*@",
        r".*marketing.*@",
        r".*@.*giftcard.*\.com",
    ]
}

# Subject keywords (checked against subject line)
SUBJECT_KEYWORDS = {
    "urgent_response": [
        "urgent", "asap", "immediately", "deadline",
        "due today", "due tomorrow", "due by",
        "permit", "inspection", "code violation",
        "action required", "response needed",
    ],
    "needs_response": [
        "question", "can you", "could you", "would you",
        "please review", "feedback needed", "your input",
        "meeting request", "schedule", "availability",
        "invoice", "payment due", "renewal",
    ],
    "fyi": [
        "newsletter", "digest", "weekly update", "monthly update",
        "notification", "alert", "automated",
        "receipt", "confirmation", "order confirmed",
        "shipped", "delivered", "tracking",
        "welcome to", "getting started", "your account",
        "password reset", "verify your", "confirm your",
        "unsubscribe", "preferences",
        # Marketing/webinar/content
        "webinar", "register now", "join us for",
        "here's how", "tips for", "best practices",
        "introducing", "announcing", "what's new",
        "product update", "feature update", "release notes",
        "new feature", "now available", "just launched",
        "we're excited", "big news", "important update",
        "guide to", "how we built", "behind the scenes",
        "year in review", "wrapped", "annual report",
        "black friday", "cyber monday", "holiday",
        "early access", "beta invite", "waitlist",
    ],
    "spam": [
        "limited time", "act now", "don't miss",
        "special offer", "exclusive deal", "save %",
        "% off", "free gift", "winner", "you've won",
        "claim your", "last chance", "expires soon",
        "hot deal", "best price", "lowest price",
    ],
}


def extract_email_address(from_field: str) -> str:
    """Extract just the email address from a From field like 'Name <email@domain.com>'"""
    match = re.search(r'<([^>]+)>', from_field)
    if match:
        return match.group(1).lower()
    # No angle brackets, assume it's just the email
    return from_field.strip().lower()


def classify_by_sender(from_field: str) -> Optional[str]:
    """Classify based on sender patterns."""
    from_lower = from_field.lower()
    email_only = extract_email_address(from_field)

    for category, patterns in SENDER_PATTERNS.items():
        for pattern in patterns:
            # Check both full from field and email-only
            if re.search(pattern, from_lower) or re.search(pattern, email_only):
                logger.debug(f"Sender match '{pattern}' -> {category}")
                return category
    return None


def classify_by_subject(subject: str) -> Optional[str]:
    """Classify based on subject keywords."""
    subject_lower = subject.lower()

    for category, keywords in SUBJECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in subject_lower:
                logger.debug(f"Subject keyword '{keyword}' -> {category}")
                return category
    return None


def classify_email(sender: str, subject: str, body_preview: str = "") -> Dict:
    """
    Main classification function. Uses pattern matching only (no AI).

    Args:
        sender: The From field (e.g., "Name <email@domain.com>")
        subject: Email subject line
        body_preview: First part of email body (currently unused but kept for API compat)

    Returns:
        {
            "category": "urgent_response|needs_response|fyi|spam",
            "reason": "why this classification",
            "suggested_action": "what to do",
            "method": "pattern"
        }
    """
    # 1. Check sender patterns first (most reliable)
    sender_result = classify_by_sender(sender)
    if sender_result:
        return {
            "category": sender_result,
            "reason": f"Sender pattern match",
            "suggested_action": get_default_action(sender_result),
            "method": "pattern"
        }

    # 2. Check subject keywords
    subject_result = classify_by_subject(subject)
    if subject_result:
        return {
            "category": subject_result,
            "reason": f"Subject keyword match",
            "suggested_action": get_default_action(subject_result),
            "method": "pattern"
        }

    # 3. Default: Unknown emails need review
    # These are potentially important since they didn't match any newsletter/spam patterns
    return {
        "category": "needs_response",
        "reason": "Unknown sender - may need review",
        "suggested_action": "Review to determine importance",
        "method": "default"
    }


def get_default_action(category: str) -> str:
    """Get default suggested action for a category."""
    actions = {
        "urgent_response": "Review and respond promptly",
        "needs_response": "Review when available",
        "fyi": "Read when convenient",
        "spam": "Consider unsubscribing"
    }
    return actions.get(category, "Review")


def is_ollama_available() -> bool:
    """Deprecated - kept for API compatibility. Always returns False."""
    return False


if __name__ == "__main__":
    # Test the classifier
    logging.basicConfig(level=logging.DEBUG)

    print("Testing pattern-based classifier (no AI)\n")
    print("=" * 60)

    test_emails = [
        # Should be urgent_response
        ("bruce@bdarchitect.net", "Permit comments due Friday", ""),
        ("ifantal@lesfantal.com", "Project update needed", ""),

        # Should be fyi
        ("Fiberon <noreply@fiberondecking.com>", "Visit us at IBS", ""),
        ("Coinbase <no-reply@mail.coinbase.com>", "Trade your takes", ""),
        ("Cre8Play <info-cre8play.com@shared1.ccsend.com>", "New catalog", ""),
        ("Uber <uber@uber.com>", "Your free meal", ""),
        ("Zoom <teamzoom@e.zoom.us>", "Last chance 40% off", ""),
        ("Microsoft365 <Microsoft365@engagement.microsoft.com>", "Start protected", ""),
        ("Wispr Flow <upcoming-invoice@wispr.ai>", "Subscription renewal", ""),
        ("Gift Card Granny <hello@engage.giftcardgranny.com>", "Welcome", ""),
        ("newsletter@company.com", "Weekly Newsletter", ""),
        ("support@github.com", "PR merged", ""),

        # Should be spam
        ("sales@marketing.promo.com", "Limited time offer!", ""),

        # Unknown - should be needs_response (safe default)
        ("john.smith@unknowndomain.com", "Quick question", ""),
    ]

    for sender, subject, body in test_emails:
        result = classify_email(sender, subject, body)
        status = "✓" if result["method"] == "pattern" else "?"
        print(f"\n{status} {sender[:50]}")
        print(f"  Subject: {subject[:40]}")
        print(f"  → {result['category']} ({result['method']})")
