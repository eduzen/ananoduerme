from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    welcome_message: str = "¡Bienvenido {user_name}! 🤖\n\nPara verificar que eres humano, por favor responde esta pregunta:\n{question}\n\nResponde solo con el número. Has sido restringido temporalmente hasta la verificación."
    captcha_question: str = (
        "¿Cuánto es {a} + {b}? (Por favor responde solo con el número)"
    )
    success_message: str = "✅ ¡Verificación exitosa! ¡Bienvenido al chat, {user_name}!"
    error_message: str = (
        "❌ Respuesta incorrecta. Por favor inténtalo de nuevo.\n{question}"
    )
    bot_starting_message: str = "🤖 Bot de Captcha de Telegram iniciando..."
    bot_detected_message: str = "🚫 Bot detectado: {user_name} (@{username}) - Los bots no están permitidos en este grupo. Eliminado automáticamente."
    bot_admin_notification: str = "⚠️ ALERTA: Bot detectado y bloqueado\n\nUsuario: {user_name}\nUsername: @{username}\nID: {user_id}\n\nEl bot ha sido restringido automáticamente."
    admin_chat_id: int | None = None
    database_path: str = "db.sqlite3"

    logfire_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
