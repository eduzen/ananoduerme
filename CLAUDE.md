# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram captcha bot called "ananoduerme" that provides anti-spam protection for Telegram groups. The project uses Python 3.13+ with modern async/await patterns and SQLite for persistent data storage.

## Development Commands

### Running the Application
```bash
python main.py
```

### Python Environment
- Python version: 3.13+ (specified in .python-version)
- Dependencies managed via uv script header in main.py
- Required packages: httpx>=0.28.1, pydantic-settings>=2.10.1
- Uses pyproject.toml for project configuration

### Environment Setup
Create a `.env` file with:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_PATH=bot_users.db  # optional, defaults to bot_users.db
```

## Project Structure

### Core Files
- `main.py` - Entry point and application orchestration
- `settings.py` - Configuration management using Pydantic
- `telegram_bot.py` - Main bot logic and Telegram API interactions
- `database.py` - SQLite database operations and persistence layer

### Supporting Files
- `pyproject.toml` - Project configuration and metadata
- `.python-version` - Specifies Python 3.13 for version management tools
- `.gitignore` - Standard Python gitignore covering common build artifacts and virtual environments
- `bot_users.db` - SQLite database (created automatically)

## Architecture Notes

### Modular Design
The codebase is organized into separate modules for better maintainability:
- **Settings**: Centralized configuration with environment variable support
- **Database**: Persistent storage for user verification states
- **TelegramBot**: Core bot functionality and message handling
- **Main**: Application entry point and coordination

### Database Schema
SQLite database with two main tables:
- `users`: Tracks user verification status (verified/pending/blocked)
- `pending_verifications`: Active captcha challenges with questions/answers

### Bot Features
- **Captcha Verification**: Math-based challenges for new users
- **Bot Detection**: Automatic blocking of bot accounts
- **Persistent State**: User verification survives bot restarts
- **Admin Notifications**: Private alerts to group administrators
- **Leave/Rejoin Handling**: Proper cleanup and state management

## Dependency Management
- Uses uv script dependencies defined in main.py header
- Modern Python 3.13+ syntax throughout
- No external package manager files needed

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
- `DATABASE_PATH`: SQLite database file path (default: bot_users.db)
- Message templates for welcome, success, error, and admin notifications

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
