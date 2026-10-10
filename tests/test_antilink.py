from unittest.mock import MagicMock

from app.services.antilink import check_link_violation, extract_domains_and_links


def test_extract_domains_and_links():
    msg = MagicMock()
    msg.text = "Check this site https://google.com and t.me/telegram"
    msg.caption = None
    msg.entities = []
    msg.caption_entities = []

    links, domains = extract_domains_and_links(msg)
    assert len(links) >= 2
    assert "google.com" in domains
    assert "t.me" in domains


def test_check_link_violation_with_allowlist():
    domains = {"youtube.com"}
    rules = [("youtube.com", "allow")]

    # When anti_link is ON but domain is allowed
    is_violating, offending = check_link_violation(
        domains, rules, anti_link_enabled=True
    )
    assert is_violating is False
    assert offending is None


def test_check_link_violation_with_blocklist():
    domains = {"phishing-site.xyz"}
    rules = [("phishing-site.xyz", "block")]

    # Even if anti_link is OFF, blocklist must trigger
    is_violating, offending = check_link_violation(
        domains, rules, anti_link_enabled=False
    )
    assert is_violating is True
    assert offending == "phishing-site.xyz"


def test_check_link_violation_default_blocking():
    domains = {"randomlink.com"}
    rules = []

    # anti_link is ON, no rule exists -> violation
    is_violating, offending = check_link_violation(
        domains, rules, anti_link_enabled=True
    )
    assert is_violating is True
    assert offending == "randomlink.com"
