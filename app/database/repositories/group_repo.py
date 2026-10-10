from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    BlockedWord,
    DomainRule,
    Group,
    GroupSettings,
    KeywordReaction,
)


async def get_or_create_group(
    session: AsyncSession,
    chat_id: int,
    title: str,
    username: str | None = None,
    chat_type: str = "supergroup",
    bot_is_admin: bool = False,
) -> tuple[Group, GroupSettings]:
    """Retrieves existing group and settings or registers new ones idempotently."""
    stmt = select(Group).where(Group.id == chat_id)
    res = await session.execute(stmt)
    group = res.scalar_one_or_none()

    if not group:
        group = Group(
            id=chat_id,
            title=title,
            username=username,
            chat_type=chat_type,
            is_active=True,
            bot_is_admin=bot_is_admin,
        )
        session.add(group)
        settings = GroupSettings(
            group_id=chat_id,
            welcome_text="Welcome {name} to {title}! Please respect the group rules.",
            goodbye_text="Goodbye {name}!",
        )
        session.add(settings)
        await session.commit()
        await session.refresh(group)
        await session.refresh(settings)
        return group, settings
    else:
        # Update metadata if changed
        group.title = title
        if username:
            group.username = username
        group.is_active = True
        group.bot_is_admin = bot_is_admin

        # Fetch settings
        settings_stmt = select(GroupSettings).where(GroupSettings.group_id == chat_id)
        settings_res = await session.execute(settings_stmt)
        settings = settings_res.scalar_one_or_none()
        if not settings:
            settings = GroupSettings(
                group_id=chat_id,
                welcome_text="Welcome {name} to {title}! Please respect the group rules.",
                goodbye_text="Goodbye {name}!",
            )
            session.add(settings)
        await session.commit()
        await session.refresh(group)
        await session.refresh(settings)
        return group, settings


async def get_group_settings(
    session: AsyncSession, chat_id: int
) -> GroupSettings | None:
    stmt = select(GroupSettings).where(GroupSettings.group_id == chat_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def update_group_settings(
    session: AsyncSession, chat_id: int, **kwargs
) -> GroupSettings | None:
    settings = await get_group_settings(session, chat_id)
    if not settings:
        return None
    for k, v in kwargs.items():
        if hasattr(settings, k):
            setattr(settings, k, v)
    await session.commit()
    await session.refresh(settings)
    return settings


async def get_active_groups(session: AsyncSession) -> list[Group]:
    stmt = select(Group).where(Group.is_active == True)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_keyword_reactions(session: AsyncSession, chat_id: int) -> dict[str, str]:
    stmt = select(KeywordReaction).where(
        KeywordReaction.group_id == chat_id, KeywordReaction.is_active == True
    )
    res = await session.execute(stmt)
    return {r.keyword: r.emoji for r in res.scalars().all()}


async def add_keyword_reaction(
    session: AsyncSession, chat_id: int, keyword: str, emoji: str
) -> KeywordReaction:
    normalized = keyword.strip().lower()
    stmt = select(KeywordReaction).where(
        KeywordReaction.group_id == chat_id, KeywordReaction.keyword == normalized
    )
    res = await session.execute(stmt)
    reaction = res.scalar_one_or_none()
    if reaction:
        reaction.emoji = emoji
        reaction.is_active = True
    else:
        reaction = KeywordReaction(group_id=chat_id, keyword=normalized, emoji=emoji)
        session.add(reaction)
    await session.commit()
    await session.refresh(reaction)
    return reaction


async def remove_keyword_reaction(
    session: AsyncSession, chat_id: int, keyword: str
) -> bool:
    normalized = keyword.strip().lower()
    stmt = delete(KeywordReaction).where(
        KeywordReaction.group_id == chat_id, KeywordReaction.keyword == normalized
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0


async def get_blocked_words(session: AsyncSession, chat_id: int) -> list[str]:
    stmt = select(BlockedWord.word).where(BlockedWord.group_id == chat_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def add_blocked_word(
    session: AsyncSession, chat_id: int, word: str
) -> BlockedWord:
    normalized = word.strip().lower()
    stmt = select(BlockedWord).where(
        BlockedWord.group_id == chat_id, BlockedWord.word == normalized
    )
    res = await session.execute(stmt)
    entry = res.scalar_one_or_none()
    if not entry:
        entry = BlockedWord(group_id=chat_id, word=normalized)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
    return entry


async def remove_blocked_word(session: AsyncSession, chat_id: int, word: str) -> bool:
    normalized = word.strip().lower()
    stmt = delete(BlockedWord).where(
        BlockedWord.group_id == chat_id, BlockedWord.word == normalized
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0


async def get_domain_rules(
    session: AsyncSession, chat_id: int
) -> list[tuple[str, str]]:
    stmt = select(DomainRule.domain, DomainRule.rule_type).where(
        DomainRule.group_id == chat_id
    )
    res = await session.execute(stmt)
    return list(res.all())


async def add_domain_rule(
    session: AsyncSession, chat_id: int, domain: str, rule_type: str = "allow"
) -> DomainRule:
    clean_domain = (
        domain.strip()
        .lower()
        .replace("http://", "")
        .replace("https://", "")
        .split("/")[0]
    )
    stmt = select(DomainRule).where(
        DomainRule.group_id == chat_id, DomainRule.domain == clean_domain
    )
    res = await session.execute(stmt)
    rule = res.scalar_one_or_none()
    if rule:
        rule.rule_type = rule_type
    else:
        rule = DomainRule(group_id=chat_id, domain=clean_domain, rule_type=rule_type)
        session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def remove_domain_rule(session: AsyncSession, chat_id: int, domain: str) -> bool:
    clean_domain = (
        domain.strip()
        .lower()
        .replace("http://", "")
        .replace("https://", "")
        .split("/")[0]
    )
    stmt = delete(DomainRule).where(
        DomainRule.group_id == chat_id, DomainRule.domain == clean_domain
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0
