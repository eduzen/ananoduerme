import asyncio
from typing import Any
from database import Database
from bot_detection import BotDetector


class CommandHandler:
    def __init__(self, bot_instance, db: Database, bot_detector: BotDetector):
        self.bot = bot_instance
        self.db = db
        self.bot_detector = bot_detector

    async def handle_command(self, message: dict[str, Any]) -> None:
        """Handle bot commands"""
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        # Parse command
        command = text.split()[0].lower()

        if command == "/banned" or command == "/listbanned":
            await self.handle_list_banned_command(chat_id, user_id)

    async def handle_list_banned_command(self, chat_id: int, user_id: int) -> None:
        """Handle the /banned command to list blocked users"""
        # Check if user is admin
        if not await self.bot.is_user_admin(chat_id, user_id):
            await self.bot.send_message(
                chat_id, "❌ Only administrators can use this command."
            )
            return

        # Get blocked users
        blocked_users = self.db.get_blocked_users()

        if not blocked_users:
            await self.bot.send_message(chat_id, "✅ No banned users found.")
            return

        # Format the message
        message_lines = ["🚫 Banned Users List:\n\n"]

        for i, user in enumerate(blocked_users, 1):
            username_display = f"@{user.username}" if user.username else "sin_username"
            user_line = f"{i}. {user.name} ({username_display})\n"
            user_line += f"   ID: {user.id}\n"
            user_line += f"   Banned: {user.created_at[:19]}\n\n"
            message_lines.append(user_line)

        # Split message if too long (Telegram limit is 4096 characters)
        full_message = "".join(message_lines)

        if len(full_message) <= 4096:
            await self.bot.send_message(chat_id, full_message)
        else:
            # Split into chunks
            chunks = []
            current_chunk = "🚫 Banned Users List:\n\n"

            for line in message_lines[1:]:  # Skip the header
                if len(current_chunk + line) > 4000:  # Leave some buffer
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += line

            if current_chunk:
                chunks.append(current_chunk)

            # Send chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await self.bot.send_message(chat_id, chunk)
                else:
                    await self.bot.send_message(
                        chat_id, f"🚫 Banned Users List (continued):\n\n{chunk}"
                    )

    async def handle_scan_users_command(self, chat_id: int, user_id: int) -> None:
        """Handle the /scanusers command to scan all users for bots"""
        # Check if user is admin
        if not await self.bot.is_user_admin(chat_id, user_id):
            await self.bot.send_message(
                chat_id, "❌ Only administrators can use this command."
            )
            return

        # Send initial message
        await self.bot.send_message(chat_id, "🔍 Starting user scan for bots...")

        # Get all users from database
        users = self.db.get_all_users_for_scanning()

        if not users:
            await self.bot.send_message(
                chat_id,
                "📭 No users found in database. Users are added when they join the group. Use /scanallchatmembers to scan current group members.",
            )
            return

        scan_stats = {
            "total_users": len(users),
            "bots_detected": 0,
            "api_errors": 0,
        }

        bot_detection_results = []

        # Send progress message
        await self.bot.send_message(chat_id, f"👥 Scanning {len(users)} users...")

        for i, user in enumerate(users, 1):
            # Scan user for bot detection
            scan_result = await self.bot_detector.scan_user_for_bot(user.id)

            if scan_result.get("reason") == "API_ERROR":
                scan_stats["api_errors"] += 1
                continue

            # Check if user is a bot
            if scan_result["is_bot"]:
                scan_stats["bots_detected"] += 1

                # Add to detection results
                bot_detection_results.append(
                    {
                        "user_id": user.id,
                        "user_name": user.name,
                        "username": user.username,
                        "current_status": user.status,
                        "detection_reason": scan_result["reason"],
                    }
                )

                # Update database to mark as blocked
                self.db.add_blocked_user(user.id, user.name, user.username)

            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.1)

        # Send results
        await self._send_scan_results(chat_id, scan_stats, bot_detection_results)

    async def _send_scan_results(
        self,
        chat_id: int,
        scan_stats: dict[str, int],
        bot_detection_results: list[dict[str, Any]],
    ) -> None:
        """Send scan results to the chat"""
        result_lines = [
            "📊 USER SCAN RESULTS\n",
            f"📈 Total users scanned: {scan_stats['total_users']}",
            f"🤖 New bots detected: {scan_stats['bots_detected']}",
            f"❌ API errors: {scan_stats['api_errors']}\n",
        ]

        if bot_detection_results:
            result_lines.append("🚨 DETECTED BOTS:")
            for i, bot in enumerate(
                bot_detection_results[:10], 1
            ):  # Limit to 10 for message length
                username_display = (
                    f"@{bot['username']}" if bot["username"] else "sin_username"
                )
                result_lines.append(f"{i}. {bot['user_name']} ({username_display})")
                result_lines.append(f"   Reason: {bot['detection_reason']}")

            if len(bot_detection_results) > 10:
                result_lines.append(
                    f"\n... and {len(bot_detection_results) - 10} more bots detected"
                )
        else:
            result_lines.append("✅ No new bots detected!")

        result_lines.append("\n✅ Scan complete! Database updated.")

        full_message = "\n".join(result_lines)

        # Split message if too long
        if len(full_message) <= 4096:
            await self.bot.send_message(chat_id, full_message)
        else:
            # Send in chunks
            chunks = []
            current_chunk = ""

            for line in result_lines:
                if len(current_chunk + line + "\n") > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"

            if current_chunk:
                chunks.append(current_chunk)

            for chunk in chunks:
                await self.bot.send_message(chat_id, chunk)

    async def handle_scan_all_chat_members_command(
        self, chat_id: int, user_id: int
    ) -> None:
        """Handle the /scanallchatmembers command to scan all current chat members"""
        # Check if user is admin
        if not await self.bot.is_user_admin(chat_id, user_id):
            await self.bot.send_message(
                chat_id, "❌ Only administrators can use this command."
            )
            return

        # Send initial message
        await self.bot.send_message(
            chat_id, "🔍 Scanning all current chat members for bots..."
        )

        try:
            # Get chat members count first
            members_count = await self.bot.get_chat_members_count(chat_id)
            await self.bot.send_message(
                chat_id, f"👥 Chat has {members_count} members. Starting scan..."
            )

            # Get chat administrators to know who to skip
            admins = await self.bot.get_chat_administrators(chat_id)
            admin_ids = {admin["user"]["id"] for admin in admins}

            scan_stats = {
                "total_scanned": 0,
                "bots_detected": 0,
                "api_errors": 0,
                "admins_skipped": 0,
            }

            bot_detection_results = []

            # For supergroups, we can't enumerate all members easily
            # So we'll scan the users we know about plus any we encounter
            # This is a limitation of the Telegram Bot API
            await self.bot.send_message(
                chat_id,
                "⚠️ Note: Telegram Bot API doesn't allow enumerating all chat members. "
                "I can only scan users who have interacted with me or are in my database.",
            )

            # Scan users from database first
            users = self.db.get_all_users_for_scanning()
            if users:
                await self.bot.send_message(
                    chat_id, f"🔍 Found {len(users)} users in database to scan..."
                )

                for user in users:
                    # Skip if user is an admin
                    if user.id in admin_ids:
                        scan_stats["admins_skipped"] += 1
                        continue

                    # Skip if user is the bot itself
                    if user.id == self.bot.bot_user_id:
                        continue

                    # Scan user for bot detection
                    scan_result = await self.bot_detector.scan_user_for_bot(user.id)
                    scan_stats["total_scanned"] += 1

                    if scan_result.get("reason") == "API_ERROR":
                        scan_stats["api_errors"] += 1
                        continue

                    # Check if user is a bot
                    if scan_result["is_bot"]:
                        scan_stats["bots_detected"] += 1

                        # Add to detection results
                        bot_detection_results.append(
                            {
                                "user_id": user.id,
                                "user_name": user.name,
                                "username": user.username,
                                "current_status": user.status,
                                "detection_reason": scan_result["reason"],
                            }
                        )

                        # Update database to mark as blocked
                        self.db.add_blocked_user(user.id, user.name, user.username)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)

            # Send final results
            await self._send_scan_all_results(
                chat_id, scan_stats, bot_detection_results
            )

        except Exception as e:
            await self.bot.send_message(chat_id, f"❌ Error during scan: {str(e)}")

    async def _send_scan_all_results(
        self,
        chat_id: int,
        scan_stats: dict[str, int],
        bot_detection_results: list[dict[str, Any]],
    ) -> None:
        """Send scan all results to the chat"""
        result_lines = [
            "📊 CHAT MEMBER SCAN RESULTS\n",
            f"📈 Total users scanned: {scan_stats['total_scanned']}",
            f"🤖 New bots detected: {scan_stats['bots_detected']}",
            f"❌ API errors: {scan_stats['api_errors']}",
            f"👑 Admins skipped: {scan_stats['admins_skipped']}\n",
        ]

        if bot_detection_results:
            result_lines.append("🚨 DETECTED BOTS:")
            for i, bot in enumerate(
                bot_detection_results[:10], 1
            ):  # Limit to 10 for message length
                username_display = (
                    f"@{bot['username']}" if bot["username"] else "sin_username"
                )
                result_lines.append(f"{i}. {bot['user_name']} ({username_display})")
                result_lines.append(f"   Reason: {bot['detection_reason']}")

            if len(bot_detection_results) > 10:
                result_lines.append(
                    f"\n... and {len(bot_detection_results) - 10} more bots detected"
                )
        else:
            result_lines.append("✅ No new bots detected!")

        result_lines.append("\n✅ Scan complete! Database updated.")

        full_message = "\n".join(result_lines)

        # Split message if too long
        if len(full_message) <= 4096:
            await self.bot.send_message(chat_id, full_message)
        else:
            # Send in chunks
            chunks = []
            current_chunk = ""

            for line in result_lines:
                if len(current_chunk + line + "\n") > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"

            if current_chunk:
                chunks.append(current_chunk)

            for chunk in chunks:
                await self.bot.send_message(chat_id, chunk)
