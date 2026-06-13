import logging
import aiohttp
from typing import Optional, List, Dict, Any
from tgbot import db

logger = logging.getLogger(__name__)

async def add_channel_for_user(user_id: int, channel_id: int, channel_name: str) -> None:
    """Inserts or replaces channel association for a user."""
    # Ensure the table entry is correct
    await db.execute(
        "INSERT OR REPLACE INTO channels (user_id, channel_id, channel_name) VALUES (?, ?, ?)",
        (user_id, channel_id, channel_name)
    )
    logger.info(f"Registered channel {channel_name} ({channel_id}) for user {user_id}")

async def remove_channel_for_user(user_id: int, channel_id: int) -> bool:
    """Removes a channel association."""
    result = await db.execute(
        "DELETE FROM channels WHERE user_id = ? AND channel_id = ?",
        (user_id, channel_id)
    )
    return result > 0

async def get_user_channels(user_id: int) -> List[Dict[str, Any]]:
    """Gets list of all channels configured by user."""
    return await db.fetch_all("SELECT * FROM channels WHERE user_id = ?", (user_id,))

async def add_shortener_for_user(user_id: int, api_url: str, api_token: str) -> None:
    """Configures a custom shortener for a user."""
    await db.execute(
        "INSERT OR REPLACE INTO shorteners (user_id, api_url, api_token) VALUES (?, ?, ?)",
        (user_id, api_url, api_token)
    )
    logger.info(f"Configured shortener API {api_url} for user {user_id}")

async def get_user_shortener(user_id: int) -> Optional[Dict[str, Any]]:
    """Gets customized shortener configuration if set up by user."""
    return await db.fetch_one("SELECT * FROM shorteners WHERE user_id = ?", (user_id,))

async def get_bot_setting(key: str, default: str) -> str:
    """Reads a direct bot setting from SQLite key-value store."""
    row = await db.fetch_one("SELECT value FROM bot_settings WHERE key = ?", (key,))
    return row["value"] if row else default

async def set_bot_setting(key: str, value: str) -> None:
    """Writes a bot setting."""
    await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, str(value)))

async def shorten_url_via_custom_shortener(api_url: str, api_token: str, long_url: str) -> Optional[str]:
    """Helper method to shorten dynamic links using GPLinks / customized tools."""
    # Build standard query parameters
    # Standard format: api_url?api=token&url=long_url
    url = f"{api_url.rstrip('/')}"
    params = {
        "api": api_token,
        "url": long_url
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=8) as r:
                if r.status in [200, 201]:
                    data = await r.json()
                    # Safe check standard keys: shortenedUrl, short_url, or URL
                    return data.get("shortenedUrl") or data.get("short_url") or data.get("url")
    except Exception as e:
        logger.error(f"Error shortening URL via custom API shortener: {e}")
    return None
