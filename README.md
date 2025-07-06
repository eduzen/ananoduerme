# ananoduerme - Telegram Captcha Bot

A Telegram captcha bot that provides anti-spam protection for Telegram groups through math-based verification challenges.

## Features

- **Captcha Verification**: Math-based challenges for new users
- **Bot Detection**: Automatic blocking of bot accounts
- **Persistent State**: User verification survives bot restarts
- **Admin Notifications**: Private alerts to group administrators
- **Leave/Rejoin Handling**: Proper cleanup and state management

## Quick Start

### 1. Environment Setup

Create a `.env` file:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_PATH=bot_users.db
```

### 2. Run the Bot

```bash
python main.py
```

### 3. Add Bot to Groups

**⚠️ CRITICAL: Bot Admin Requirements**

The bot **MUST** be added as an administrator to Telegram groups with these permissions:

- ✅ **Delete messages** - Required to remove spam and captcha messages
- ✅ **Ban users** - Required to kick users who fail captcha verification
- ✅ **Restrict members** - Required to limit new user permissions during verification

**Without these admin permissions, the bot will NOT work properly.**

#### Setup Steps:
1. Add the bot to your Telegram group
2. Go to group settings → Administrators
3. Promote the bot to administrator
4. Enable all three permissions listed above
5. The bot will automatically start monitoring new members

## Requirements

- Python 3.13+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Admin permissions in target Telegram groups

## Project Structure

- `main.py` - Entry point and application orchestration
- `settings.py` - Configuration management
- `telegram_bot.py` - Main bot logic and Telegram API interactions
- `database.py` - SQLite database operations

## How It Works

1. **New Member Joins**: Bot detects new group members
2. **Captcha Challenge**: Sends math question to verify human users
3. **Verification**: Users must solve the captcha within time limit
4. **Action**: Bot kicks users who fail verification or are detected as bots
5. **Cleanup**: Removes captcha messages after successful verification

## Database

Uses SQLite with automatic schema creation:
- `users` table: Tracks verification status
- `pending_verifications` table: Active captcha challenges

Database file is created automatically on first run.
