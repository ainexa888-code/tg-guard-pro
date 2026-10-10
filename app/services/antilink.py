import re
from urllib.parse import urlparse

from aiogram.types import Message

URL_REGEX = re.compile(
    r"(?i)\b(?:(?:https?://|ftp://|tg://|t\.me/|telegram\.me/)"
    r"|(?:\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|org|net|edu|gov|mil|xyz|top|site|club|vip|online|info|ru|cn|in|me|io|co|biz|tv|cc|ly|gg)\b)"
    r"[^\s<>]*",
    re.IGNORECASE,
)

TELEGRAM_INVITE_REGEX = re.compile(
    r"(?i)(?:t\.me/|telegram\.me/|tg://join\?invite=)([a-zA-Z0-9_\+]+)",
    re.IGNORECASE,
)


def extract_domains_and_links(message: Message) -> tuple[list[str], set[str]]:
    """
    Extracts all raw URLs and unique normalized domain names from a Telegram message,
    including raw text, caption, and hidden entity text_links.
    """
    text = (message.text or "") + " " + (message.caption or "")
    detected_links: list[str] = []
    detected_domains: set[str] = set()

    # 1. Regex search over text and caption
    for match in URL_REGEX.finditer(text):
        link = match.group(0).rstrip(".,;:!?)")
        detected_links.append(link)
        domain = _extract_clean_domain(link)
        if domain:
            detected_domains.add(domain)

    # 2. Check entities (including hyperlinks hidden in text)
    entities = (message.entities or []) + (message.caption_entities or [])
    for entity in entities:
        if entity.type == "url":
            raw_url = text[entity.offset : entity.offset + entity.length]
            detected_links.append(raw_url)
            domain = _extract_clean_domain(raw_url)
            if domain:
                detected_domains.add(domain)
        elif entity.type == "text_link" and entity.url:
            detected_links.append(entity.url)
            domain = _extract_clean_domain(entity.url)
            if domain:
                detected_domains.add(domain)

    return detected_links, detected_domains


def _extract_clean_domain(url: str) -> str | None:
    """Extracts lowercase domain name without scheme, port, or path."""
    if not url:
        return None
    if not url.startswith(("http://", "https://", "tg://", "ftp://")):
        url = "http://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        # Remove port if present
        domain = domain.split(":")[0].lower().strip()
        return domain if "." in domain or domain in ("t.me", "telegram.me") else None
    except Exception:
        return None


def check_link_violation(
    detected_domains: set[str],
    domain_rules: list[tuple[str, str]],  # [(domain, rule_type), ...]
    anti_link_enabled: bool,
) -> tuple[bool, str | None]:
    """
    Evaluates whether any detected domain violates group policies.
    Returns (is_violating, offending_domain).
    """
    if not detected_domains:
        return False, None

    allowlist: set[str] = set()
    blocklist: set[str] = set()

    for d, rule in domain_rules:
        clean = d.lower().strip()
        if rule == "allow":
            allowlist.add(clean)
        elif rule == "block":
            blocklist.add(clean)

    for domain in detected_domains:
        # Check explicit blocklist first
        if any(domain == b or domain.endswith("." + b) for b in blocklist):
            return True, domain

        # If anti_link is ON, domain must be in allowlist
        if anti_link_enabled:
            is_allowed = any(domain == a or domain.endswith("." + a) for a in allowlist)
            if not is_allowed:
                return True, domain

    return False, None
