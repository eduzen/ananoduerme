# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram captcha bot called "ananoduerme" that provides anti-spam protection for Telegram groups. The project uses Python 3.13+ with modern async/await patterns and SQLite for persistent data storage.

## Development Commands

### Running the Application
```bash
uv run main.py
# or use justfile
just run
```

### Python Environment
- Python version: 3.13+ (specified in .python-version)
- Required packages: httpx>=0.28.1, pydantic-settings>=2.10.1, rich>=14.0.0
- Uses pyproject.toml for project configuration with uv dependency management
- **Always use uv to run Python app and also Python commands**

### Development Commands
```bash
# Run the application
just run

# Format code (runs pre-commit hooks)
just fmt

# Type checking
just type-check

# Show database contents
just show_db
```

### Environment Setup
Create a `.env` file with:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_PATH=db.sqlite3  # optional, defaults to db.sqlite3
```

## Project Structure

### Core Files
- `main.py` - Entry point and application orchestration
- `settings.py` - Configuration management using Pydantic
- `telegram_bot.py` - Main bot logic and Telegram API interactions
- `database.py` - SQLite database operations and persistence layer
- `commands.py` - Bot command handlers (admin commands)
- `bot_detection.py` - Bot detection logic and utilities
- `scan_users.py` - Standalone script for scanning existing users

### Supporting Files
- `pyproject.toml` - Project configuration and metadata
- `justfile` - Task runner with common development commands
- `.python-version` - Specifies Python 3.13 for version management tools
- `.gitignore` - Standard Python gitignore covering common build artifacts and virtual environments
- `db.sqlite3` - SQLite database (created automatically)

## Architecture Notes

### Modular Design
The codebase is organized into separate modules for better maintainability:
- **Settings**: Centralized configuration with environment variable support
- **Database**: Persistent storage for user verification states
- **TelegramBot**: Core bot functionality and message handling
- **Main**: Application entry point and coordination

### Database Schema
SQLite database with two main tables:
- `users`: Tracks user verification status (verified/pending/blocked) with chat_id context
- `pending_verifications`: Active captcha challenges with questions/answers

Key database features:
- Generic `upsert_user()` method for all user status updates
- Automatic timestamp updates via SQL triggers
- Indexed queries for performance
- Foreign key constraints for data integrity

### Bot Features
- **Captcha Verification**: Math-based challenges for new users
- **Bot Detection**: Automatic blocking of bot accounts
- **Persistent State**: User verification survives bot restarts
- **Admin Notifications**: Private alerts to group administrators
- **Leave/Rejoin Handling**: Proper cleanup and state management
- **Admin Commands**: Special commands for group administrators

### Admin Commands
Available to group administrators only:
- `/banned` or `/listbanned` - List all banned/blocked users
- `/scanusers` - Scan all database users to detect and block bots automatically

## Dependency Management
- Uses uv for Python package management with pyproject.toml
- Dependencies split into main and dev groups
- Modern Python 3.13+ syntax throughout
- Development dependencies include pre-commit hooks and type checking

## Type Hints and Python 3.13+ Notes
- Uses modern Python 3.13+ syntax: `dict[str, Any]` instead of `Dict[str, Any]`
- Union types with `|` operator: `str | None` instead of `Optional[str]`
- All functions and methods have proper type annotations
- Async/await patterns for non-blocking I/O operations

## Database Operations
- Automatic schema creation on first run
- Indexed queries for performance
- Proper connection management with context handling
- User state persistence across bot restarts

## Configuration Options
All settings configurable via environment variables:
- `TELEGRAM_BOT_TOKEN`: Required bot token from @BotFather
- `DATABASE_PATH`: SQLite database file path (default: db.sqlite3)
- Message templates for welcome, success, error, and admin notifications

## Bot Setup Requirements

### Admin Permissions
**IMPORTANT**: The bot must be added as an administrator to Telegram groups with the following permissions:
- **Delete messages**: Required to remove spam and captcha messages
- **Ban users**: Required to kick users who fail captcha verification
- **Restrict members**: Required to limit new user permissions during verification

Without these admin permissions, the bot cannot function properly and will be unable to:
- Remove captcha messages after verification
- Kick users who fail verification or are detected as bots
- Enforce verification requirements on new members

### Adding the Bot to Groups
1. Add the bot to your Telegram group
2. Promote the bot to administrator
3. Enable the required permissions listed above
4. The bot will automatically start monitoring new members

## Key Implementation Details

### Database Patterns
- All user operations use the generic `upsert_user(user_id, user_name, status, username=None, chat_id=None)` method
- Legacy methods `add_verified_user()`, `add_blocked_user()` delegate to `upsert_user()`
- Database file name is configured in `settings.py` as `database_path` (defaults to "db.sqlite3")
- Supports context manager pattern: `with Database(path) as db: ...`

### Bot Detection System
- Two-tier bot detection: instant (via Telegram API) and analysis-based (username patterns)
- Standalone `scan_users.py` script for batch processing existing users
- Bot detection integrated into admin commands via `/scanusers`

### Architecture Flow
1. `main.py` orchestrates startup and creates all service instances
2. `telegram_bot.py` handles Telegram API interactions and message routing
3. `commands.py` provides admin-only functionality via `CommandHandler`
4. `database.py` provides centralized data operations with the `upsert_user()` pattern
5. `bot_detection.py` provides reusable bot detection logic used by both real-time and batch processes

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
