import asyncio
import logging
import logfire
from rich.console import Console
from settings import Settings
from telegram_bot import TelegramBot

console = Console()
settings = Settings()

# configure logfire
logfire.configure(token=settings.logfire_token)
logfire.instrument_sqlite3()
logfire.instrument_httpx()

# Reduce httpx logging verbosity
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main() -> None:
    try:
        console.print(
            f"[green]✅ Bot token loaded:[/green] [cyan]{settings.telegram_bot_token[:10]}...[/cyan]"
        )
        console.print(
            f"[blue]🔧 Welcome message:[/blue] [dim]{settings.welcome_message[:50]}...[/dim]"
        )
        console.print(
            f"[blue]🔧 Captcha question:[/blue] [yellow]{settings.captcha_question}[/yellow]"
        )
        bot = TelegramBot(settings.telegram_bot_token, settings)
        await bot.run()
    except Exception as e:
        console.print(f"[red]❌ Error loading settings:[/red] [dim]{e}[/dim]")
        console.print(
            "[yellow]Make sure to create a .env file with TELEGRAM_BOT_TOKEN[/yellow]"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n\n[red]🛑 ¡Hasta luego! Bot detenido por el usuario.[/red]")
        console.print("[blue]👋 Gracias por usar el bot de captcha[/blue]")
