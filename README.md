# 🛡️ Group Predictor Bot V4

**Super Admin Control Center, Live Monitoring & Multi-Group Security Platform**

Repository: [ainexa888-code/tg-guard-pro](https://github.com/ainexa888-code/tg-guard-pro)

Group Predictor Bot V4 is an enterprise-grade, asynchronous Telegram group security system engineered using Python 3.11+, Aiogram 3.x, SQLAlchemy 2 Async, Alembic, PostgreSQL, and SQLite. It provides multi-group isolation, 24-module Master Control Center (`/master`), Triple Ownership Engine (`/crownme`, `/coowner`), 1-Click Admin Shifting (`/shiftadmin`, `/shiftowner`, `/evacuateadmins`), Ghost Spy Logging, Traitor Admin Trap, Emergency Nuke (`/nuke`), and Dead Man's Switch recovery.

---

## ✨ Features (मुख्य विशेषताएँ)

1. **Multi-Group Isolation:** Supports hundreds of groups independently with dedicated rules, settings, reaction dictionaries, domain rules, and audit logs.
2. **Interactive 16-Module Dashboard (`/panel`):**
   - 🏢 Group Overview
   - 👮 Admin Management
   - 🛡️ Security Settings
   - ⚡ Keyword Auto Reactions
   - 🔤 Fancy Font Filter (Safe for Hindi/Arabic/Tamil scripts)
   - 🚫 Anti-Spam (Flood, Duplicates, Emojis, Mentions)
   - 🔗 Anti-Link Protection (Custom domain allowlist & blocklist)
   - 👋 Welcome & Goodbye Automation (Auto-deleting notices)
   - 🤖 Captcha Verification (Button & Math challenges, restart-safe)
   - 🚨 Anti-Raid System (Join burst detection & auto-lockdown)
   - 🤬 Bad Word Filter (Unicode-aware word boundary matching)
   - ⏳ Persistent Auto-Delete Scheduler
   - 📊 Group Analytics (`/stats`, 7d, 30d reporting)
   - 📋 Admin Audit Logs with Pagination
   - 📢 Multi-Group Broadcast (Strict admin opt-in enforcement)
   - 💚 Bot System Health & Diagnostics
3. **Owner & Admin Security:** Enforces Telegram API administrator permissions on every action and callback query. Global operators cannot bypass group administrator boundaries.
4. **Resilient Scheduling:** Database-backed persistent deletion worker that survives container restarts.
5. **Zero Downtime 24/7 Deployment:** Fully configured for Render Background Worker long-polling.

---

## 🛠️ Tech Stack

- **Framework:** Python 3.11+ / Aiogram 3.x
- **Database:** PostgreSQL (Production) / SQLite Async (Testing)
- **ORM & Migrations:** SQLAlchemy 2.0 Async, Asyncpg, Alembic
- **Caching:** Redis / High-performance in-memory fallback
- **Hosting:** Render Background Worker (Single-consumer long polling)
- **Testing & Quality:** Pytest, Pytest-Asyncio, Ruff

---

## 📋 Bot Commands (कमांड सूची)

### Administration & Moderation
- `/admins` — ग्रुप एडमिनिस्ट्रेटर सूची देखें
- `/ban` — यूजर को ग्रुप से बैन करें (रिप्लाई या User ID)
- `/unban <id>` — यूजर को अनबैन करें
- `/mute [min]` — यूजर को म्यूट करें (डिफ़ॉल्ट 60 मिनट)
- `/unmute` — यूजर को अनम्यूट करें
- `/warn [reason]` — यूजर को आधिकारिक चेतावनी दें (एस्केलेशन सहित)
- `/warnings` — वर्तमान चेतावनियाँ देखें
- `/resetwarn` — चेतावनियाँ रीसेट करें
- `/pin` & `/unpin` — मैसेज पिन/अनपिन करें
- `/logs` — हालिया ऑडिट लॉग्स देखें
- `/panel` या `/dashboard` — इंटरएक्टिव कंट्रोल पैनल खोलें

### Security & Modules
- `/reaction on|off|add <kw> <emoji>|remove <kw>|list|test <kw>`
- `/font on|off|mode warn|mode delete`
- `/antispam on|off`, `/spamlimit <num>`, `/warnlimit <num>`
- `/antilink on|off`, `/allowdomain <dom>`, `/blockdomain <dom>`, `/allowlist`
- `/welcome on|off`, `/setwelcome <text>`, `/goodbye on|off`
- `/captcha on|off`, `/captcha timeout <sec>`
- `/antiraid on|off`, `/raidlimit <num>`
- `/badword on|off|add <word>|remove <word>|list`
- `/stats [7d|30d]`
- `/broadcast <msg>` (Bot Owner only)
- `/broadcastoptin` & `/broadcastoptout`

---

## 🚀 Quickstart & Local Setup

```bash
# 1. Clone repository
git clone https://github.com/harshit234211/tg-guard-pro.git
cd tg-guard-pro

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your BOT_TOKEN, OWNER_ID, and DATABASE_URL

# 5. Initialize database
python scripts/init_db.py

# 6. Run automated test suite
pytest -v tests/

# 7. Start Bot
python app/main.py
```

---

## 🔒 Security & Script Safety

- **Native Script Protection:** Mathematical Stylized Alphanumeric Unicode symbols (Fraktur, Bold Script, Circled) are moderated without impacting native writing scripts such as Hindi (Devanagari), Tamil, Bengali, Arabic, Cyrillic, or Chinese.
- **XSS/HTML Sanitization:** User strings are safely escaped using `sanitize_telegram_html` to prevent Telegram markup injection attacks.
- **Strict Permission Verification:** Moderation callbacks and commands verify live Telegram administrator permissions before execution.

---

## 📄 License
MIT License. Crafted for resilient Telegram community protection.
