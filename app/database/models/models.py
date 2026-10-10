import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram User ID
    username = Column(String(64), nullable=True, index=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Group(Base):
    __tablename__ = "groups"

    id = Column(
        BigInteger, primary_key=True, index=True
    )  # Telegram Chat ID (e.g. -100...)
    title = Column(String(255), nullable=False)
    username = Column(String(64), nullable=True)
    chat_type = Column(String(32), default="supergroup")
    is_active = Column(Boolean, default=True)
    bot_is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    settings = relationship(
        "GroupSettings",
        back_populates="group",
        uselist=False,
        cascade="all, delete-orphan",
    )
    reactions = relationship(
        "KeywordReaction", back_populates="group", cascade="all, delete-orphan"
    )
    blocked_words = relationship(
        "BlockedWord", back_populates="group", cascade="all, delete-orphan"
    )
    domain_rules = relationship(
        "DomainRule", back_populates="group", cascade="all, delete-orphan"
    )


class GroupSettings(Base):
    __tablename__ = "group_settings"

    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    language = Column(String(10), default="hi")  # "hi" or "en"

    # Fancy font
    fancy_font_detection = Column(Boolean, default=True)
    fancy_font_action = Column(String(20), default="warn")  # "warn", "delete", "mute"

    # Anti-spam
    anti_spam = Column(Boolean, default=True)
    spam_limit = Column(Integer, default=5)  # messages per interval
    spam_interval = Column(Integer, default=5)  # seconds
    warn_limit = Column(Integer, default=3)
    warn_action = Column(String(20), default="mute")  # "mute", "ban", "kick"

    # Anti-link
    anti_link = Column(Boolean, default=True)

    # Welcome & Goodbye
    welcome_enabled = Column(Boolean, default=True)
    welcome_text = Column(Text, nullable=True)
    goodbye_enabled = Column(Boolean, default=False)
    goodbye_text = Column(Text, nullable=True)

    # Captcha
    captcha_enabled = Column(Boolean, default=True)
    captcha_mode = Column(String(20), default="button")  # "button" or "math"
    captcha_timeout = Column(Integer, default=120)  # seconds

    # Anti-raid
    anti_raid = Column(Boolean, default=True)
    raid_limit = Column(Integer, default=15)  # joins in raid_window
    raid_window = Column(Integer, default=60)  # seconds

    # Bad word filter
    bad_word_filter = Column(Boolean, default=True)
    bad_word_action = Column(String(20), default="delete")  # "delete", "warn"

    # Auto-reactions
    auto_reactions = Column(Boolean, default=True)
    reaction_mode = Column(String(20), default="keyword")
    reaction_cooldown = Column(Integer, default=10)

    # Audit & Auto-delete
    admin_logs = Column(Boolean, default=True)
    auto_delete_welcome = Column(Boolean, default=True)
    auto_delete_duration = Column(Integer, default=60)

    # Broadcast & Night Mode
    broadcast_optin = Column(Boolean, default=True)
    night_mode = Column(Boolean, default=False)
    night_mode_start = Column(String(10), default="23:00")
    night_mode_end = Column(String(10), default="06:00")

    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    group = relationship("Group", back_populates="settings")


class GroupAdminCache(Base):
    __tablename__ = "group_admin_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id = Column(BigInteger, index=True)
    custom_title = Column(String(64), nullable=True)
    is_owner = Column(Boolean, default=False)
    can_restrict_members = Column(Boolean, default=True)
    can_delete_messages = Column(Boolean, default=True)
    cached_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_admin_cache_group_user", "group_id", "user_id"),)


class KeywordReaction(Base):
    __tablename__ = "keyword_reactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    keyword = Column(String(64), nullable=False)
    emoji = Column(String(16), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    group = relationship("Group", back_populates="reactions")

    __table_args__ = (
        UniqueConstraint("group_id", "keyword", name="uq_group_reaction_keyword"),
    )


class BlockedWord(Base):
    __tablename__ = "blocked_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    word = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    group = relationship("Group", back_populates="blocked_words")

    __table_args__ = (
        UniqueConstraint("group_id", "word", name="uq_group_blocked_word"),
    )


class DomainRule(Base):
    __tablename__ = "domain_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    domain = Column(String(255), nullable=False)
    rule_type = Column(String(16), default="allow")  # "allow" or "block"
    created_at = Column(DateTime(timezone=True), default=utc_now)

    group = relationship("Group", back_populates="domain_rules")

    __table_args__ = (
        UniqueConstraint("group_id", "domain", name="uq_group_domain_rule"),
    )


class MemberWarning(Base):
    __tablename__ = "member_warnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id = Column(BigInteger, index=True)
    reason = Column(String(255), default="Violation of group rules")
    warned_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_warnings_group_user", "group_id", "user_id"),)


class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id = Column(BigInteger, index=True)
    challenge_type = Column(String(20), default="button")
    answer = Column(String(64), nullable=False)
    message_id = Column(BigInteger, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_solved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_captcha_group_user", "group_id", "user_id"),)


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id = Column(BigInteger, index=True)
    action = Column(
        String(32), nullable=False
    )  # "warn", "mute", "unmute", "ban", "unban", "kick"
    reason = Column(String(255), nullable=True)
    admin_id = Column(BigInteger, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    actor_id = Column(BigInteger, nullable=True)
    target_id = Column(BigInteger, nullable=True)
    action = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class GroupDailyStat(Base):
    __tablename__ = "group_daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    stat_date = Column(Date, default=lambda: date.today(), index=True)
    messages_count = Column(Integer, default=0)
    active_users_count = Column(Integer, default=0)
    joins_count = Column(Integer, default=0)
    leaves_count = Column(Integer, default=0)
    spam_blocked_count = Column(Integer, default=0)
    links_blocked_count = Column(Integer, default=0)
    fonts_blocked_count = Column(Integer, default=0)
    badwords_blocked_count = Column(Integer, default=0)
    captcha_success_count = Column(Integer, default=0)
    captcha_failed_count = Column(Integer, default=0)
    reactions_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("group_id", "stat_date", name="uq_group_daily_stat"),
    )


class BroadcastCampaign(Base):
    __tablename__ = "broadcast_campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(BigInteger, nullable=False)
    message_text = Column(Text, nullable=False)
    status = Column(
        String(20), default="draft"
    )  # "draft", "sending", "completed", "cancelled"
    total_groups = Column(Integer, default=0)
    successful_groups = Column(Integer, default=0)
    failed_groups = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    deliveries = relationship(
        "BroadcastDelivery", back_populates="campaign", cascade="all, delete-orphan"
    )


class BroadcastDelivery(Base):
    __tablename__ = "broadcast_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(
        String(36), ForeignKey("broadcast_campaigns.id", ondelete="CASCADE"), index=True
    )
    group_id = Column(BigInteger, index=True)
    status = Column(String(20), default="pending")  # "sent", "failed", "skipped"
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    campaign = relationship("BroadcastCampaign", back_populates="deliveries")


class ScheduledDeletion(Base):
    __tablename__ = "scheduled_deletions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, index=True)
    message_id = Column(BigInteger, index=True)
    delete_at = Column(DateTime(timezone=True), index=True)
    reason = Column(String(64), nullable=True)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, index=True)
    event_type = Column(String(64), nullable=False)
    severity = Column(String(20), default="warning")  # "info", "warning", "critical"
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
