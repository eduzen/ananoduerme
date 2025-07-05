import asyncio
from settings import Settings
from telegram_bot import TelegramBot

settings = Settings()


async def main() -> None:
    try:
        print(f"✅ Bot token loaded: {settings.telegram_bot_token[:10]}...")
        print(f"🔧 Welcome message: {settings.welcome_message[:50]}...")
        print(f"🔧 Captcha question: {settings.captcha_question}")
        bot = TelegramBot(settings.telegram_bot_token, settings)
        await bot.run()
    except KeyboardInterrupt:
        print("\n\n🛑 ¡Hasta luego! Bot detenido por el usuario.")
        print("👋 Gracias por usar el bot de captcha")
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        print("Make sure to create a .env file with TELEGRAM_BOT_TOKEN")


if __name__ == "__main__":
    asyncio.run(main())
