import pytest

from app.database.repositories.moderation_repo import get_captcha_challenge
from app.services.captcha import CaptchaService


@pytest.mark.asyncio
async def test_captcha_generation_and_persistence(test_session, mock_bot):
    chat_id = -100555
    user_id = 999

    challenge_id, correct_ans, kb = await CaptchaService.create_and_restrict(
        bot=mock_bot,
        session=test_session,
        chat_id=chat_id,
        user_id=user_id,
        mode="button",
        timeout_seconds=60,
    )

    # Verify persistent record in database
    challenge = await get_captcha_challenge(test_session, challenge_id)
    assert challenge is not None
    assert challenge.user_id == user_id
    assert challenge.answer == correct_ans
    assert challenge.is_solved is False


@pytest.mark.asyncio
async def test_captcha_verification_success(test_session, mock_bot):
    chat_id = -100555
    user_id = 999

    challenge_id, correct_ans, _ = await CaptchaService.create_and_restrict(
        bot=mock_bot,
        session=test_session,
        chat_id=chat_id,
        user_id=user_id,
        mode="button",
        timeout_seconds=60,
    )

    # Correct answer
    success, msg = await CaptchaService.verify_answer(
        bot=mock_bot,
        session=test_session,
        challenge_id=challenge_id,
        user_id=user_id,
        submitted_answer=correct_ans,
    )
    assert success is True
    # Verify unmuted in mock
    mock_bot.restrict_chat_member.assert_called()


@pytest.mark.asyncio
async def test_captcha_verification_failure(test_session, mock_bot):
    chat_id = -100555
    user_id = 999

    challenge_id, correct_ans, _ = await CaptchaService.create_and_restrict(
        bot=mock_bot,
        session=test_session,
        chat_id=chat_id,
        user_id=user_id,
        mode="button",
        timeout_seconds=60,
    )

    # Wrong answer
    wrong_ans = "INCORRECT_VALUE"
    success, msg = await CaptchaService.verify_answer(
        bot=mock_bot,
        session=test_session,
        challenge_id=challenge_id,
        user_id=user_id,
        submitted_answer=wrong_ans,
    )
    assert success is False
