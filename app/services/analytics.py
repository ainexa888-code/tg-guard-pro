from app.database.repositories.analytics_repo import (
    get_stats_summary,
    increment_daily_stat,
)
from app.database.session import AsyncSessionLocal


class AnalyticsService:
    @staticmethod
    async def record_event(chat_id: int, event_field: str, amount: int = 1) -> None:
        """Increments a metric counter asynchronously in the database."""
        async with AsyncSessionLocal() as session:
            await increment_daily_stat(session, chat_id, event_field, amount)

    @staticmethod
    async def format_analytics_report(
        chat_id: int, days: int = 7, language: str = "hi"
    ) -> str:
        """Generates an honest, clear analytics summary report."""
        async with AsyncSessionLocal() as session:
            data = await get_stats_summary(session, chat_id, days=days)

        if language == "hi":
            return (
                f"📊 <b>ग्रुप एनालिटिक्स रिपोर्ट (पिछले {days} दिन)</b>\n"
                f"<i>(नोट: यह डेटा बॉट द्वारा मॉनिटर की गई गतिविधियों पर आधारित है)</i>\n\n"
                f"💬 कुल मैसेज देखे गए: <b>{data['total_messages']}</b>\n"
                f"📥 नए सदस्य शामिल हुए: <b>{data['total_joins']}</b>\n"
                f"📤 सदस्य छोड़कर गए: <b>{data['total_leaves']}</b>\n\n"
                f"🛡️ <b>सुरक्षा और मॉडरेशन:</b>\n"
                f"• स्पैम ब्लॉक किए गए: <b>{data['spam_blocked']}</b>\n"
                f"• अनधिकृत लिंक हटाए गए: <b>{data['links_blocked']}</b>\n"
                f"• फैंसी फॉन्ट्स डिटेक्ट हुए: <b>{data['fonts_blocked']}</b>\n"
                f"• अभद्र शब्द (Bad words) हटाए: <b>{data['badwords_blocked']}</b>\n"
                f"• सफल कैप्चा वेरिफिकेशन: <b>{data['captcha_success']}</b>\n"
                f"• असफल/टाइमआउट कैप्चा: <b>{data['captcha_failed']}</b>\n"
                f"• कीवर्ड ऑटो-रिएक्शन: <b>{data['reactions_count']}</b>\n\n"
                f"⚙️ <i>TG GUARD PRO V3 द्वारा सुरक्षित</i>"
            )
        else:
            return (
                f"📊 <b>Group Analytics Report (Last {days} Days)</b>\n"
                f"<i>(Note: Based solely on observed activity while bot was active)</i>\n\n"
                f"💬 Observed Messages: <b>{data['total_messages']}</b>\n"
                f"📥 New Members Joined: <b>{data['total_joins']}</b>\n"
                f"📤 Members Left: <b>{data['total_leaves']}</b>\n\n"
                f"🛡️ <b>Security & Moderation:</b>\n"
                f"• Spam Blocked: <b>{data['spam_blocked']}</b>\n"
                f"• Links Blocked: <b>{data['links_blocked']}</b>\n"
                f"• Fancy Fonts Detected: <b>{data['fonts_blocked']}</b>\n"
                f"• Bad Words Blocked: <b>{data['badwords_blocked']}</b>\n"
                f"• Captcha Verified: <b>{data['captcha_success']}</b>\n"
                f"• Captcha Failed/Timed Out: <b>{data['captcha_failed']}</b>\n"
                f"• Keyword Reactions Applied: <b>{data['reactions_count']}</b>\n\n"
                f"⚙️ <i>Secured by TG GUARD PRO V3</i>"
            )
