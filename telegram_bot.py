import asyncio
import random
from typing import Any
import httpx
from rich.console import Console
from database import Database
from bot_detection import BotDetector
from commands import CommandHandler
from settings import Settings

console = Console()


class TelegramBot:
    def __init__(self, token: str, settings: Settings) -> None:
        self.token = token
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.db = Database(settings.database_path)
        self.bot_user_id: int | None = None

        # Initialize bot detector and command handler
        self.bot_detector = BotDetector(token)
        self.command_handler = CommandHandler(self, self.db, self.bot_detector)

        # Print database statistics on startup
        counts = self.db.get_user_counts()
        console.print(
            f"[blue]📊 Database loaded:[/blue] [green]{counts['verified']} verified[/green], [red]{counts['blocked']} blocked[/red], [yellow]{counts['pending_verifications']} pending[/yellow]"
        )

    async def get_updates(self, offset: int = 0) -> list[dict[str, Any]]:
        """Get updates from Telegram using long polling"""
        async with httpx.AsyncClient(timeout=35.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                result = response.json()

                # Check if the API call was successful
                if not result.get("ok", False):
                    error_msg = result.get("description", "Unknown error")
                    raise Exception(f"Telegram API error: {error_msg}")

                return result.get("result", [])
            except httpx.ReadTimeout:
                # This is normal for long polling - return empty list
                return []

    async def get_me(self) -> dict[str, Any]:
        """Get bot information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getMe")
            result = response.json()
            return result.get("result", {})

    async def send_message(
        self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a message to a chat"""
        async with httpx.AsyncClient() as client:
            data = {"chat_id": chat_id, "text": text}
            if reply_markup:
                data["reply_markup"] = reply_markup

            response = await client.post(f"{self.base_url}/sendMessage", json=data)
            return response.json()

    async def restrict_user(self, chat_id: int, user_id: int) -> dict[str, Any]:
        """Restrict user from sending messages"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/restrictChatMember",
                json={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "permissions": {
                        "can_send_messages": False,
                        "can_send_media_messages": False,
                        "can_send_polls": False,
                        "can_send_other_messages": False,
                        "can_add_web_page_previews": False,
                        "can_change_info": False,
                        "can_invite_users": False,
                        "can_pin_messages": False,
                    },
                },
            )
            return response.json()

    async def unrestrict_user(self, chat_id: int, user_id: int) -> dict[str, Any]:
        """Remove restrictions from user"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/restrictChatMember",
                json={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "permissions": {
                        "can_send_messages": True,
                        "can_send_media_messages": True,
                        "can_send_polls": True,
                        "can_send_other_messages": True,
                        "can_add_web_page_previews": True,
                        "can_change_info": True,
                        "can_invite_users": True,
                        "can_pin_messages": True,
                    },
                },
            )
            return response.json()

    async def kick_chat_member(self, chat_id: int, user_id: int) -> dict[str, Any]:
        """Kick a user from the chat"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/banChatMember",
                json={
                    "chat_id": chat_id,
                    "user_id": user_id,
                },
            )
            result = response.json()
            console.print(
                f"[yellow]User kick attempt:[/yellow] [cyan]{response.status_code}[/cyan], Response: [dim]{result}[/dim]"
            )
            return result

    async def get_chat_administrators(self, chat_id: int) -> list[dict[str, Any]]:
        """Get list of chat administrators"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getChatAdministrators", params={"chat_id": chat_id}
            )
            result = response.json()
            return result.get("result", [])

    async def get_chat_members_count(self, chat_id: int) -> int:
        """Get the number of members in a chat"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getChatMembersCount", params={"chat_id": chat_id}
            )
            result = response.json()
            return result.get("result", 0)

    async def is_user_admin(self, chat_id: int, user_id: int) -> bool:
        """Check if user is an administrator in the chat"""
        try:
            admins = await self.get_chat_administrators(chat_id)
            for admin in admins:
                if admin["user"]["id"] == user_id:
                    return True
            return False
        except Exception:
            return False

    async def notify_admins(self, chat_id: int, message: str) -> None:
        """Send a message to all administrators"""
        try:
            admins = await self.get_chat_administrators(chat_id)
            for admin in admins:
                # Don't notify bots (including our own bot)
                if not admin["user"]["is_bot"]:
                    admin_id = admin["user"]["id"]
                    try:
                        await self.send_message(admin_id, message)
                    except Exception as e:
                        # Admin might have blocked the bot or doesn't allow DMs
                        # Log the error for debugging purposes
                        console.print(
                            f"[red]Error sending message to admin {admin_id}:[/red] [dim]{e}[/dim]"
                        )
                        pass
        except Exception as e:
            console.print(f"[red]Error notifying admins:[/red] [dim]{e}[/dim]")

    async def handle_bot_user(
        self, chat_id: int, user_id: int, user_name: str, username: str | None = None
    ) -> None:
        """Handle bot users - restrict and notify admins"""
        console.print(
            f"[red bold]🚨 HANDLE_BOT_USER called for:[/red bold] [yellow]{user_name}[/yellow] [dim](ID: {user_id})[/dim]"
        )

        if self.db.is_user_blocked(user_id):
            console.print(
                f"[yellow]⚠️ Bot {user_name} already in blocked list, skipping...[/yellow]"
            )
            return

        console.print(
            f"[red]🔒 Restricting bot user:[/red] [yellow]{user_name}[/yellow]"
        )
        # Restrict the bot user
        await self.restrict_user(chat_id, user_id)
        self.db.add_blocked_user(user_id, user_name, username)

        # Format username for display
        username_display = username if username else "sin_username"
        console.print("[blue]📢 Sending public bot detection message...[/blue]")

        # Send public message about bot detection
        public_message = self.settings.bot_detected_message.format(
            user_name=user_name, username=username_display
        )
        console.print(f"[blue]📧 Public message:[/blue] [dim]{public_message}[/dim]")
        await self.kick_chat_member(chat_id, user_id)

        await self.send_message(chat_id, public_message)

    def generate_captcha(self) -> tuple[str, str]:
        """Generate a simple math captcha question"""
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        question = self.settings.captcha_question.format(a=a, b=b)
        answer = str(a + b)
        return question, answer

    async def handle_left_member(
        self, chat_id: int, user_id: int, user_name: str
    ) -> None:
        """Handle member leaving the chat"""
        console.print(
            f"[yellow]👋 HANDLE_LEFT_MEMBER called for:[/yellow] [cyan]{user_name}[/cyan] [dim](ID: {user_id})[/dim]"
        )

        # Clean up pending verification if user was pending
        if self.db.get_pending_verification(user_id):
            console.print(
                f"[blue]🧹 Cleaning up pending verification for:[/blue] [cyan]{user_name}[/cyan]"
            )
            self.db.remove_pending_verification(user_id)

        # Keep verified users in the database so they don't get re-restricted when rejoining
        if self.db.is_user_verified(user_id):
            console.print(
                f"[green]✅ Keeping verified status for:[/green] [cyan]{user_name}[/cyan]"
            )

        # Remove from blocked bots if they somehow leave
        if self.db.is_user_blocked(user_id):
            console.print(
                f"[red]🤖 Removing from blocked bots:[/red] [cyan]{user_name}[/cyan]"
            )
            self.db.remove_user(user_id)

    async def handle_new_member(
        self,
        chat_id: int,
        user_id: int,
        user_name: str,
        is_bot: bool = False,
        username: str | None = None,
    ) -> None:
        """Handle new member joining the chat"""
        console.print(
            f"[green bold]🚀 HANDLE_NEW_MEMBER called with:[/green bold] [cyan]user_name={user_name}[/cyan], [blue]user_id={user_id}[/blue], [yellow]is_bot={is_bot}[/yellow], [magenta]username={username}[/magenta]"
        )

        # Skip processing if this is the bot itself
        if user_id == self.bot_user_id:
            console.print(
                f"[dim]🤖 Skipping self (this bot):[/dim] [cyan]{user_name}[/cyan]"
            )
            return

        # Check if the new member is a bot FIRST (bots should NEVER be verified)
        if is_bot:
            console.print(
                f"[red bold]🤖 BOT USER DETECTED:[/red bold] [yellow]{user_name}[/yellow] - [red]Processing as bot...[/red]"
            )
            # Remove from verified users if somehow they were added before
            # (Database will handle this with the blocked status)
            await self.handle_bot_user(chat_id, user_id, user_name, username)
            return

        # Only check verified users for humans
        if self.db.is_user_verified(user_id):
            console.print(
                f"[green]✅ Human user already verified:[/green] [cyan]{user_name}[/cyan] - [green]SKIPPING restriction[/green]"
            )
            return

        console.print(
            f"[cyan]👤 Processing human user:[/cyan] [yellow]{user_name}[/yellow]"
        )
        counts = self.db.get_user_counts()
        console.print(
            f"[blue]🔍 Current verified users:[/blue] [green]{counts['verified']} users[/green]"
        )
        console.print(
            f"[blue]🔍 Current pending users:[/blue] [yellow]{counts['pending_verifications']} users[/yellow]"
        )
        console.print(
            f"[blue]🔍 User {user_id} verified:[/blue] [green]{self.db.is_user_verified(user_id)}[/green]"
        )
        console.print(
            f"[blue]🔍 User {user_id} pending:[/blue] [yellow]{self.db.get_pending_verification(user_id) is not None}[/yellow]"
        )

        # Check if user is already pending verification
        pending_data = self.db.get_pending_verification(user_id)
        if pending_data:
            console.print(
                f"[yellow]⏳ User {user_name} already has pending verification - SKIPPING new captcha[/yellow]"
            )
            # Just remind them of the existing question
            remind_message = self.settings.welcome_message.format(
                user_name=user_name, question=pending_data["question"]
            ).replace("\\n", "\n")
            await self.send_message(chat_id, remind_message)
            return

        # Restrict the user immediately
        await self.restrict_user(chat_id, user_id)

        # Generate captcha
        question, answer = self.generate_captcha()

        # Store pending verification in database
        self.db.add_pending_verification(user_id, chat_id, user_name, question, answer)

        # Send captcha question
        welcome_message = self.settings.welcome_message.format(
            user_name=user_name, question=question
        ).replace("\\n", "\n")

        await self.send_message(chat_id, welcome_message)

    async def handle_message(self, message: dict[str, Any]) -> None:
        """Handle incoming messages"""
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        is_bot = message["from"].get("is_bot", False)

        # Ignore messages from bots (they shouldn't be able to answer captchas anyway)
        if is_bot:
            return

        # Check for admin commands
        if text.startswith("/"):
            await self.command_handler.handle_command(message)
            return

        # Check if user is pending verification
        user_data = self.db.get_pending_verification(user_id)
        if user_data:
            if text.strip() == user_data["answer"]:
                # Correct answer - verify user
                await self.unrestrict_user(chat_id, user_id)
                self.db.add_verified_user(user_id, user_data["user_name"])
                self.db.remove_pending_verification(user_id)

                await self.send_message(
                    chat_id,
                    self.settings.success_message.format(
                        user_name=user_data["user_name"]
                    ),
                )
            else:
                # Wrong answer
                await self.send_message(
                    chat_id,
                    self.settings.error_message.format(
                        question=user_data["question"]
                    ).replace("\\n", "\n"),
                )

    async def handle_update(self, update: dict[str, Any]) -> None:
        """Handle a single update from Telegram"""
        console.print(f"[dim]🔍 Raw update: {update}[/dim]")

        if "message" in update:
            message = update["message"]
            console.print(f"[dim]📝 Message received: {message}[/dim]")

            # Check for left chat members
            if "left_chat_member" in message:
                console.print("[yellow]👋 LEFT CHAT MEMBER DETECTED![/yellow]")
                chat_id = message["chat"]["id"]
                console.print(f"[blue]🏠 Chat ID:[/blue] [cyan]{chat_id}[/cyan]")

                member = message["left_chat_member"]
                user_id = member["id"]
                user_name = member.get("first_name", "User")
                console.print(
                    f"[blue]🔍 Left member:[/blue] [yellow]{user_name}[/yellow] [dim](ID: {user_id})[/dim]"
                )
                console.print(f"[dim]📋 Full member data: {member}[/dim]")
                await self.handle_left_member(chat_id, user_id, user_name)

            # Check for new chat members
            elif "new_chat_members" in message:
                console.print("[green]👥 NEW CHAT MEMBERS DETECTED![/green]")
                chat_id = message["chat"]["id"]
                console.print(f"[blue]🏠 Chat ID:[/blue] [cyan]{chat_id}[/cyan]")

                for member in message["new_chat_members"]:
                    user_id = member["id"]
                    user_name = member.get("first_name", "User")
                    is_bot = member.get("is_bot", False)
                    username = member.get("username")
                    console.print(
                        f"[blue]🔍 New member:[/blue] [yellow]{user_name}[/yellow] [dim](ID: {user_id}, is_bot: {is_bot}, username: {username})[/dim]"
                    )
                    console.print(f"[dim]📋 Full member data: {member}[/dim]")
                    await self.handle_new_member(
                        chat_id, user_id, user_name, is_bot, username
                    )

            # Handle regular messages
            else:
                console.print(
                    f"[blue]💬 Regular message from user:[/blue] [cyan]{message.get('from', {}).get('first_name', 'Unknown')}[/cyan]"
                )
                await self.handle_message(message)
        else:
            console.print(
                f"[yellow]❓ Update without message:[/yellow] [dim]{update}[/dim]"
            )

    async def run(self) -> None:
        """Main bot loop"""
        console.print(f"[green]{self.settings.bot_starting_message}[/green]")

        # Get bot's own user ID to avoid processing itself
        if not self.bot_user_id:
            bot_info = await self.get_me()
            self.bot_user_id = bot_info.get("id")
            console.print(
                f"[green]🤖 Bot initialized:[/green] [cyan]{bot_info.get('first_name', 'Unknown')}[/cyan] [dim](ID: {self.bot_user_id})[/dim]"
            )

        offset = 0

        try:
            while True:
                try:
                    updates = await self.get_updates(offset)

                    if updates:
                        console.print(
                            f"[blue]📨 Received {len(updates)} updates[/blue]"
                        )

                    for update in updates:
                        console.print(
                            f"[blue]🔄 Processing update:[/blue] [cyan]{update.get('update_id', 'unknown')}[/cyan]"
                        )
                        await self.handle_update(update)
                        offset = update["update_id"] + 1

                    if not updates:
                        await asyncio.sleep(1)

                except KeyboardInterrupt:
                    console.print("\n[red]🛑 Bot stopping...[/red]")
                    break
                except Exception as e:
                    console.print(
                        f"[red]Error: {type(e).__name__}:[/red] [dim]{e}[/dim]"
                    )
                    import traceback

                    traceback.print_exc()
                    await asyncio.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[red]🛑 Bot stopped by user[/red]")
        finally:
            console.print("[blue]👋 Bot shutdown complete[/blue]")
