# /// script
# name = "ananoduerme"
# version = "0.1.0"
# description = "Add your description here"
# readme = "README.md"
# requires-python = ">=3.13"
# dependencies = [
#     "httpx>=0.28.1",
#     "pydantic-settings>=2.10.1",
# ]
# ///
#
import asyncio
import random
import signal
import sys
from typing import Dict, Set
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    welcome_message: str = "¡Bienvenido {user_name}! 🤖\n\nPara verificar que eres humano, por favor responde esta pregunta:\n{question}\n\nResponde solo con el número. Has sido restringido temporalmente hasta la verificación."
    captcha_question: str = "¿Cuánto es {a} + {b}? (Por favor responde solo con el número)"
    success_message: str = "✅ ¡Verificación exitosa! ¡Bienvenido al chat, {user_name}!"
    error_message: str = "❌ Respuesta incorrecta. Por favor inténtalo de nuevo.\n{question}"
    bot_starting_message: str = "🤖 Bot de Captcha de Telegram iniciando..."
    bot_detected_message: str = "🚫 Bot detectado: {user_name} (@{username}) - Los bots no están permitidos en este grupo."
    bot_admin_notification: str = "⚠️ ALERTA: Bot detectado y bloqueado\n\nUsuario: {user_name}\nUsername: @{username}\nID: {user_id}\n\nEl bot ha sido restringido automáticamente."

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')



class TelegramBot:
    def __init__(self, token: str, settings: Settings):
        self.token = token
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.pending_users: Dict[int, Dict] = {}  # user_id -> {chat_id, question, answer}
        self.verified_users: Set[int] = set()
        self.blocked_bots: Set[int] = set()
        self.bot_user_id: int = None

    async def get_updates(self, offset: int = 0) -> list:
        """Get updates from Telegram using long polling"""
        async with httpx.AsyncClient(timeout=35.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": offset, "timeout": 30}
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

    async def get_me(self) -> dict:
        """Get bot information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getMe")
            result = response.json()
            return result.get("result", {})

    async def send_message(self, chat_id: int, text: str, reply_markup=None):
        """Send a message to a chat"""
        async with httpx.AsyncClient() as client:
            data = {"chat_id": chat_id, "text": text}
            if reply_markup:
                data["reply_markup"] = reply_markup

            response = await client.post(f"{self.base_url}/sendMessage", json=data)
            return response.json()

    async def restrict_user(self, chat_id: int, user_id: int):
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
                        "can_pin_messages": False
                    }
                }
            )
            return response.json()

    async def unrestrict_user(self, chat_id: int, user_id: int):
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
                        "can_pin_messages": True
                    }
                }
            )
            return response.json()

    async def get_chat_administrators(self, chat_id: int) -> list:
        """Get list of chat administrators"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getChatAdministrators", params={"chat_id": chat_id})
            result = response.json()
            return result.get("result", [])

    async def notify_admins(self, chat_id: int, message: str):
        """Send a message to all administrators"""
        try:
            admins = await self.get_chat_administrators(chat_id)
            for admin in admins:
                # Don't notify bots (including our own bot)
                if not admin["user"]["is_bot"]:
                    admin_id = admin["user"]["id"]
                    try:
                        await self.send_message(admin_id, message)
                    except:
                        # Admin might have blocked the bot or doesn't allow DMs
                        pass
        except Exception as e:
            print(f"Error notifying admins: {e}")

    async def handle_bot_user(self, chat_id: int, user_id: int, user_name: str, username: str = None):
        """Handle bot users - restrict and notify admins"""
        print(f"🚨 HANDLE_BOT_USER called for: {user_name} (ID: {user_id})")
        
        if user_id in self.blocked_bots:
            print(f"⚠️ Bot {user_name} already in blocked list, skipping...")
            return

        print(f"🔒 Restricting bot user: {user_name}")
        # Restrict the bot user
        await self.restrict_user(chat_id, user_id)
        self.blocked_bots.add(user_id)

        # Format username for display
        username_display = username if username else "sin_username"
        print(f"📢 Sending public bot detection message...")

        # Send public message about bot detection
        public_message = self.settings.bot_detected_message.format(
            user_name=user_name,
            username=username_display
        )
        print(f"📧 Public message: {public_message}")
        await self.send_message(chat_id, public_message)

        print(f"👮‍♂️ Notifying admins about bot...")
        # Notify administrators privately
        admin_message = self.settings.bot_admin_notification.format(
            user_name=user_name,
            username=username_display,
            user_id=user_id
        ).replace('\\n', '\n')

        await self.notify_admins(chat_id, admin_message)

    def generate_captcha(self) -> tuple[str, str]:
        """Generate a simple math captcha question"""
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        question = self.settings.captcha_question.format(a=a, b=b)
        answer = str(a + b)
        return question, answer

    async def handle_new_member(self, chat_id: int, user_id: int, user_name: str, is_bot: bool = False, username: str = None):
        """Handle new member joining the chat"""
        print(f"🚀 HANDLE_NEW_MEMBER called with: user_name={user_name}, user_id={user_id}, is_bot={is_bot}, username={username}")
        
        # Skip processing if this is the bot itself
        if user_id == self.bot_user_id:
            print(f"🤖 Skipping self (this bot): {user_name}")
            return
        
        # Check if the new member is a bot FIRST (bots should NEVER be verified)
        if is_bot:
            print(f"🤖 BOT USER DETECTED: {user_name} - Processing as bot...")
            # Remove from verified users if somehow they were added before
            self.verified_users.discard(user_id)
            await self.handle_bot_user(chat_id, user_id, user_name, username)
            return

        # Only check verified users for humans
        if user_id in self.verified_users:
            print(f"👤 Human user already verified: {user_name}")
            return
        
        print(f"👤 Processing human user: {user_name}")

        # Restrict the user immediately
        await self.restrict_user(chat_id, user_id)

        # Generate captcha
        question, answer = self.generate_captcha()

        # Store pending verification
        self.pending_users[user_id] = {
            "chat_id": chat_id,
            "question": question,
            "answer": answer,
            "user_name": user_name
        }

        # Send captcha question
        welcome_message = self.settings.welcome_message.format(
            user_name=user_name,
            question=question
        ).replace('\\n', '\n')

        await self.send_message(chat_id, welcome_message)

    async def handle_message(self, message: dict):
        """Handle incoming messages"""
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        is_bot = message["from"].get("is_bot", False)

        # Ignore messages from bots (they shouldn't be able to answer captchas anyway)
        if is_bot:
            return

        # Check if user is pending verification
        if user_id in self.pending_users:
            user_data = self.pending_users[user_id]

            if text.strip() == user_data["answer"]:
                # Correct answer - verify user
                await self.unrestrict_user(chat_id, user_id)
                self.verified_users.add(user_id)
                del self.pending_users[user_id]

                await self.send_message(
                    chat_id,
                    self.settings.success_message.format(user_name=user_data['user_name'])
                )
            else:
                # Wrong answer
                await self.send_message(
                    chat_id,
                    self.settings.error_message.format(question=user_data['question']).replace('\\n', '\n')
                )

    async def handle_update(self, update: dict):
        """Handle a single update from Telegram"""
        print(f"🔍 Raw update: {update}")
        
        if "message" in update:
            message = update["message"]
            print(f"📝 Message received: {message}")

            # Check for new chat members
            if "new_chat_members" in message:
                print(f"👥 NEW CHAT MEMBERS DETECTED!")
                chat_id = message["chat"]["id"]
                print(f"🏠 Chat ID: {chat_id}")
                
                for member in message["new_chat_members"]:
                    user_id = member["id"]
                    user_name = member.get("first_name", "User")
                    is_bot = member.get("is_bot", False)
                    username = member.get("username")
                    print(f"🔍 New member: {user_name} (ID: {user_id}, is_bot: {is_bot}, username: {username})")
                    print(f"📋 Full member data: {member}")
                    await self.handle_new_member(chat_id, user_id, user_name, is_bot, username)

            # Handle regular messages
            else:
                print(f"💬 Regular message from user: {message.get('from', {}).get('first_name', 'Unknown')}")
                await self.handle_message(message)
        else:
            print(f"❓ Update without message: {update}")

    async def run(self):
        """Main bot loop"""
        print(self.settings.bot_starting_message)
        
        # Get bot's own user ID to avoid processing itself
        if not self.bot_user_id:
            bot_info = await self.get_me()
            self.bot_user_id = bot_info.get("id")
            print(f"🤖 Bot initialized: {bot_info.get('first_name', 'Unknown')} (ID: {self.bot_user_id})")
        
        offset = 0

        try:
            while True:
                try:
                    updates = await self.get_updates(offset)
                    
                    if updates:
                        print(f"📨 Received {len(updates)} updates")

                    for update in updates:
                        print(f"🔄 Processing update: {update.get('update_id', 'unknown')}")
                        await self.handle_update(update)
                        offset = update["update_id"] + 1

                    if not updates:
                        await asyncio.sleep(1)

                except KeyboardInterrupt:
                    print("\n🛑 Bot stopping...")
                    break
                except Exception as e:
                    print(f"Error: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        finally:
            print("👋 Bot shutdown complete")


async def main():
    try:
        settings = Settings()
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
    # Test settings loading
    from main import Settings
    settings = Settings()
    print('🔧 Settings check:')
    print('Token:', settings.telegram_bot_token[:10])
    print('Welcome:', settings.welcome_message[:30])
    print('Question:', settings.captcha_question)
    
    asyncio.run(main())
