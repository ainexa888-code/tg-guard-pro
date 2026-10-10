# 🛡️ Security Policy — TG GUARD PRO V3

TG GUARD PRO V3 enforces multi-layered cybersecurity, input sanitization, and administrative boundary controls to protect Telegram communities.

---

## 🔐 Core Security Principles

### 1. Telegram Administrator Authority
- The bot **never** bypasses Telegram's native role hierarchy.
- Moderation commands (`/ban`, `/mute`, `/warn`, `/pin`) verify live Telegram permissions for both the executing user and the bot.
- Regular group members cannot execute administrative callback queries or moderation commands.
- The global bot owner (`OWNER_ID`) manages system-level commands (`/broadcast`) but cannot override group ownership or modify settings in groups where they are not an administrator.

### 2. Multi-Group Isolation
- Database uniqueness constraints enforce strict isolation between chats.
- Group settings, warning thresholds, domain rules, blocked words, reactions, and audit logs are strictly scoped by `group_id`.
- Actions taken in Group A never affect Group B.

### 3. Secret Protection & Token Masking
- The bot token and database credentials are read exclusively from environment variables (`.env` or Render environment settings).
- Custom logging formatters automatically redact the bot token and sensitive secrets from standard stdout logs.

### 4. Input Sanitization & HTML Escaping
- All user-supplied text embedded in welcome messages, notices, and logs is sanitized via `sanitize_telegram_html` to prevent Telegram markup injection (HTML tag spoofing).

### 5. Fancy Font Unicode Moderation
- Detects stylized Mathematical Alphanumeric Unicode symbols (e.g. Fraktur, Bold/Italic script abuse) commonly utilized in malicious phishing or visual spam.
- Strictly protects legitimate international native scripts including Hindi (Devanagari), Arabic, Bengali, Tamil, Telugu, Russian (Cyrillic), and standard Latin.

---

## 🚨 Reporting Vulnerabilities

If you discover a security vulnerability, please do not file a public GitHub issue. Reach out privately to the project maintainer or support handle specified in `SUPPORT_USERNAME`.
