import random
import uuid
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.types import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.moderation_repo import (
    create_captcha_challenge,
    get_captcha_challenge,
    mark_captcha_solved,
)

CAPTCHA_ICONS = ["🍎", "🚗", "🌟", "🐱", "⚽", "🍕", "🚀", "🎸"]


class CaptchaService:
    @staticmethod
    def generate_challenge(
        mode: str = "button",
    ) -> tuple[str, str, InlineKeyboardMarkup]:
        """
        Generates a randomized challenge and corresponding inline keyboard.
        Returns (challenge_id, correct_answer, keyboard).
        """
        challenge_id = str(uuid.uuid4())[:8]

        if mode == "math":
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            correct_val = a + b
            correct_answer = str(correct_val)

            # Generate distractors
            options = {correct_val}
            while len(options) < 4:
                options.add(random.randint(2, 20))
            opt_list = list(options)
            random.shuffle(opt_list)

            buttons = [
                InlineKeyboardButton(
                    text=str(opt), callback_data=f"cpt:{challenge_id}:{opt}"
                )
                for opt in opt_list
            ]
            kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
            return challenge_id, correct_answer, kb

        else:
            # Emoji icon challenge
            target_icon = random.choice(CAPTCHA_ICONS)
            shuffled_icons = list(CAPTCHA_ICONS)
            random.shuffle(shuffled_icons)
            buttons = [
                InlineKeyboardButton(
                    text=icon, callback_data=f"cpt:{challenge_id}:{icon}"
                )
                for icon in shuffled_icons[:4]
            ]
            # Ensure target is present among the 4 options
            if target_icon not in [b.text for b in buttons]:
                buttons[0] = InlineKeyboardButton(
                    text=target_icon, callback_data=f"cpt:{challenge_id}:{target_icon}"
                )
                random.shuffle(buttons)

            kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
            return challenge_id, target_icon, kb

    @classmethod
    async def create_and_restrict(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        mode: str = "button",
        timeout_seconds: int = 120,
    ) -> tuple[str, str, InlineKeyboardMarkup]:
        """
        Restricts member temporarily and persists a captcha challenge.
        """
        # Restrict user from sending messages
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
            )
        except Exception:
            pass

        challenge_id, correct_answer, kb = cls.generate_challenge(mode)
        expires_at = datetime.now(UTC) + timedelta(seconds=timeout_seconds)

        await create_captcha_challenge(
            session=session,
            challenge_id=challenge_id,
            chat_id=chat_id,
            user_id=user_id,
            challenge_type=mode,
            answer=correct_answer,
            expires_at=expires_at,
        )

        return challenge_id, correct_answer, kb

    @classmethod
    async def verify_answer(
        cls,
        bot: Bot,
        session: AsyncSession,
        challenge_id: str,
        user_id: int,
        submitted_answer: str,
    ) -> tuple[bool, str]:
        """
        Verifies the user's submitted captcha answer.
        Returns (is_successful, message).
        """
        challenge = await get_captcha_challenge(session, challenge_id)
        if not challenge:
            return False, "Verification expired or invalid challenge."

        if challenge.user_id != user_id:
            return False, "This challenge is for another member."

        if challenge.is_solved:
            return True, "Already verified."

        now = datetime.now(UTC)
        expires = challenge.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)

        if expires < now:
            return False, "Verification timed out."

        if challenge.answer.strip() == submitted_answer.strip():
            await mark_captcha_solved(session, challenge_id)
            # Unmute user to standard permissions
            try:
                await bot.restrict_chat_member(
                    chat_id=challenge.group_id,
                    user_id=user_id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                    ),
                )
            except Exception:
                pass
            return True, "Verification successful! You can now chat."

        return False, "Incorrect answer. Please try again."
