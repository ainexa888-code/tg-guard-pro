from app.services.reactions import ReactionEngine


def test_keyword_matching_exact_and_case_insensitive():
    mapping = {
        "hello": "❤️",
        "fire": "🔥",
        "good": "👍",
        "lol": "😂",
    }

    assert ReactionEngine.match_keyword("Hello everyone!", mapping) == "❤️"
    assert ReactionEngine.match_keyword("this is FIRE", mapping) == "🔥"
    assert ReactionEngine.match_keyword("good morning", mapping) == "👍"
    assert ReactionEngine.match_keyword("LOL that is funny", mapping) == "😂"


def test_keyword_boundaries():
    mapping = {"hi": "👋"}
    # "this" or "ship" contains "hi", but boundary check should NOT trigger "hi"
    assert ReactionEngine.match_keyword("shipment has arrived", mapping) is None
    assert ReactionEngine.match_keyword("this is a test", mapping) is None
    assert ReactionEngine.match_keyword("Hi there!", mapping) == "👋"


def test_reaction_cooldown():
    chat_id = -100123
    user_id = 456
    # First reaction: allowed
    is_cd = ReactionEngine.is_cooldown_active(chat_id, user_id, cooldown_seconds=5)
    assert is_cd is False

    # Second immediate reaction: cooldown active!
    is_cd_again = ReactionEngine.is_cooldown_active(
        chat_id, user_id, cooldown_seconds=5
    )
    assert is_cd_again is True
