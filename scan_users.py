import asyncio
import sqlite3
import sys
from typing import Any
import httpx
from rich.console import Console
from rich.traceback import install
from settings import Settings
from database import Database

console = Console()
install()  # Install rich traceback handler


class UserScanner:
    def __init__(self, token: str, settings: Settings) -> None:
        self.token = token
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.db = Database(settings.database_path)
        self.bot_detection_results: list[dict[str, Any]] = []
        self.scan_stats = {
            "total_users": 0,
            "verified_users": 0,
            "pending_users": 0,
            "blocked_users": 0,
            "bots_detected": 0,
            "api_errors": 0,
        }

    async def get_user_info(self, user_id: int) -> dict[str, Any] | None:
        """Get user information from Telegram API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/getChat", params={"chat_id": user_id}
                )
                result = response.json()

                if result.get("ok"):
                    return result.get("result", {})
                else:
                    # Common error when user hasn't started a chat with the bot
                    error_desc = result.get("description", "Unknown error")
                    if "chat not found" in error_desc.lower():
                        return {"error": "chat_not_found"}
                    return {"error": error_desc}
        except Exception as e:
            return {"error": f"API request failed: {str(e)}"}

    def is_likely_bot(self, user_info: dict[str, Any]) -> tuple[bool, str]:
        """
        Analyze user information to determine if they're likely a bot
        Returns (is_bot, reason)
        """
        if user_info.get("is_bot", False):
            return True, "Confirmed bot via is_bot field"

        # Check for bot indicators in username
        username = user_info.get("username", "").lower()
        first_name = user_info.get("first_name", "").lower()

        bot_indicators = [
            "bot",
            "_bot",
            "bothelper",
            "helper",
            "admin",
            "support",
            "service",
            "notify",
            "alert",
            "spam",
            "auto",
            "system",
        ]

        for indicator in bot_indicators:
            if indicator in username or indicator in first_name:
                return True, f"Username/name contains bot indicator: '{indicator}'"

        # Check for typical bot patterns
        if username.endswith("bot"):
            return True, "Username ends with 'bot'"

        # Check for common bot naming patterns
        if any(char.isdigit() for char in username) and len(username) > 10:
            return True, "Username contains numbers and is unusually long"

        return False, "No bot indicators found"

    async def scan_all_users(self) -> None:
        """Scan all users in the database and identify potential bots"""
        console.print("[blue]🔍 Starting user scan...[/blue]")

        # Get all users from database
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, user_name, username, status, created_at
            FROM users
            ORDER BY created_at DESC
        """)

        users = cursor.fetchall()
        conn.close()

        if not users:
            console.print("[yellow]📭 No users found in database[/yellow]")
            return

        self.scan_stats["total_users"] = len(users)
        console.print(f"[green]👥 Found {len(users)} users to scan[/green]")

        for i, (user_id, user_name, username, status, created_at) in enumerate(
            users, 1
        ):
            console.print(
                f"\n[blue]🔍 Scanning user {i}/{len(users)}:[/blue] [yellow]{user_name}[/yellow] [dim](ID: {user_id})[/dim]"
            )

            # Update stats
            if status == "verified":
                self.scan_stats["verified_users"] += 1
            elif status == "pending":
                self.scan_stats["pending_users"] += 1
            elif status == "blocked":
                self.scan_stats["blocked_users"] += 1

            # Skip if already blocked
            if status == "blocked":
                console.print(
                    f"[yellow]⚠️ User {user_name} already blocked, skipping...[/yellow]"
                )
                continue

            # Get user info from Telegram
            user_info = await self.get_user_info(user_id)

            if user_info is None or "error" in user_info:
                error_msg = (
                    user_info.get("error", "Unknown error")
                    if user_info
                    else "No response"
                )
                console.print(
                    f"[red]❌ API Error for {user_name}:[/red] [dim]{error_msg}[/dim]"
                )
                self.scan_stats["api_errors"] += 1
                continue

            # Check if user is a bot
            is_bot, reason = self.is_likely_bot(user_info)

            if is_bot:
                console.print(
                    f"[red bold]🤖 BOT DETECTED:[/red bold] [yellow]{user_name}[/yellow] - [red]{reason}[/red]"
                )
                self.scan_stats["bots_detected"] += 1

                # Add to detection results
                self.bot_detection_results.append(
                    {
                        "user_id": user_id,
                        "user_name": user_name,
                        "username": username,
                        "current_status": status,
                        "created_at": created_at,
                        "detection_reason": reason,
                        "telegram_info": user_info,
                    }
                )

                # Update database to mark as blocked
                self.db.add_blocked_user(user_id, user_name, username)
                console.print(
                    f"[green]✅ Updated database: {user_name} marked as blocked[/green]"
                )
            else:
                console.print(f"[green]✅ Human user: {user_name}[/green]")

            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.1)

    def print_scan_results(self) -> None:
        """Print comprehensive scan results"""
        console.print("\n" + "=" * 60)
        console.print("[bold blue]📊 USER SCAN RESULTS[/bold blue]")
        console.print("=" * 60)

        # Print statistics
        console.print("[bold green]📈 SCAN STATISTICS:[/bold green]")
        console.print(
            f"   Total users scanned: [cyan]{self.scan_stats['total_users']}[/cyan]"
        )
        console.print(
            f"   Verified users: [green]{self.scan_stats['verified_users']}[/green]"
        )
        console.print(
            f"   Pending users: [yellow]{self.scan_stats['pending_users']}[/yellow]"
        )
        console.print(
            f"   Previously blocked: [red]{self.scan_stats['blocked_users']}[/red]"
        )
        console.print(
            f"   🤖 NEW BOTS DETECTED: [red bold]{self.scan_stats['bots_detected']}[/red bold]"
        )
        console.print(f"   API errors: [red]{self.scan_stats['api_errors']}[/red]")

        # Print detected bots
        if self.bot_detection_results:
            console.print(
                f"\n[red bold]🚨 DETECTED BOTS ({len(self.bot_detection_results)}):[/red bold]"
            )
            console.print("-" * 50)

            for i, bot in enumerate(self.bot_detection_results, 1):
                username_display = (
                    f"@{bot['username']}" if bot["username"] else "sin_username"
                )
                console.print(
                    f"[bold]{i}.[/bold] [yellow]{bot['user_name']}[/yellow] [dim]({username_display})[/dim]"
                )
                console.print(f"   ID: [cyan]{bot['user_id']}[/cyan]")
                console.print(
                    f"   Previous status: [blue]{bot['current_status']}[/blue]"
                )
                console.print(
                    f"   Detection reason: [red]{bot['detection_reason']}[/red]"
                )
                console.print(f"   Added to database: [dim]{bot['created_at']}[/dim]")
                console.print()
        else:
            console.print("\n[green]✅ No new bots detected![/green]")

        console.print("=" * 60)
        console.print("[green]✅ Scan complete! Database has been updated.[/green]")
        console.print("=" * 60)

    async def run_scan(self) -> None:
        """Run the complete user scan"""
        try:
            await self.scan_all_users()
            self.print_scan_results()

            # Save results to file for reference
            if self.bot_detection_results:
                with open("bot_detection_results.txt", "w") as f:
                    f.write("BOT DETECTION RESULTS\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Scan completed at: {asyncio.get_event_loop().time()}\n")
                    f.write(
                        f"Total bots detected: {len(self.bot_detection_results)}\n\n"
                    )

                    for i, bot in enumerate(self.bot_detection_results, 1):
                        f.write(
                            f"{i}. {bot['user_name']} (@{bot['username'] or 'sin_username'})\n"
                        )
                        f.write(f"   ID: {bot['user_id']}\n")
                        f.write(f"   Reason: {bot['detection_reason']}\n")
                        f.write(f"   Status: {bot['current_status']} -> blocked\n\n")

                console.print(
                    "[blue]📄 Results saved to:[/blue] [cyan]bot_detection_results.txt[/cyan]"
                )

        except Exception as e:
            console.print(f"[red]💥 Error during scan:[/red] [dim]{e}[/dim]")
            console.print_exception()


async def main() -> None:
    """Main function"""
    try:
        settings = Settings()
        scanner = UserScanner(settings.telegram_bot_token, settings)
        await scanner.run_scan()
    except Exception as e:
        console.print(f"[red]💥 Fatal error:[/red] [dim]{e}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
