from typing import Any
import httpx


class BotDetector:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

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

    async def scan_user_for_bot(self, user_id: int) -> dict[str, Any]:
        """
        Scan a single user and return bot detection results
        Returns dict with scan results
        """
        user_info = await self.get_user_info(user_id)

        if user_info is None or "error" in user_info:
            return {
                "user_id": user_id,
                "is_bot": False,
                "reason": "API_ERROR",
                "error": user_info.get("error", "Unknown error")
                if user_info
                else "No response",
            }

        is_bot, reason = self.is_likely_bot(user_info)

        return {
            "user_id": user_id,
            "is_bot": is_bot,
            "reason": reason,
            "user_info": user_info,
        }
