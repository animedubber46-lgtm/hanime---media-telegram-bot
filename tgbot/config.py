import os
from typing import Set, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str = ""
    tmdb_api_key: str = ""
    secret_key: str = "default_secret_key_change_me_1384"
    database_path: str = "tgbot.db"
    link_base_url: str = ""
    admin_user_ids: str = ""  # Comma-separated list of IDs
    playwright_timeout: int = 30000
    default_credits: int = 50
    stars_per_premium_day: int = 10
    bot_username: str = "HanimeBot"
    api_id: str = ""
    api_hash: str = ""
    mongodb_uri: str = ""
    owner_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix=""  # Reads direct environment variables
    )

    @property
    def admin_ids(self) -> Set[int]:
        if not self.admin_user_ids:
            return set()
        ids = set()
        for x in self.admin_user_ids.split(","):
            cleaned = x.strip()
            if cleaned.isdigit():
                ids.add(int(cleaned))
        return ids

# Instantiate settings safely
try:
    config = Settings()
    if not config.tmdb_api_key:
        config.tmdb_api_key = os.getenv("TMDB_API", os.getenv("TMDB_API_KEY", ""))
    if not config.api_id:
        config.api_id = os.getenv("API_ID", "")
    if not config.api_hash:
        config.api_hash = os.getenv("API_HASH", "")
    if not config.mongodb_uri:
        config.mongodb_uri = os.getenv("MONGODB_URI", "")
    if not config.owner_id:
        config.owner_id = os.getenv("OWNER_ID", "")
except Exception as e:
    # Fail-safe fallback if validation fails during bootstrap
    print(f"Warning: Failed to load configuration via Pydantic: {e}")
    class FallbackSettings:
        bot_token = os.getenv("BOT_TOKEN", "")
        tmdb_api_key = os.getenv("TMDB_API", os.getenv("TMDB_API_KEY", ""))
        secret_key = os.getenv("SECRET_KEY", "default_secret_key_change_me_1384")
        database_path = os.getenv("DATABASE_PATH", "tgbot.db")
        link_base_url = os.getenv("LINK_BASE_URL", "")
        admin_user_ids = os.getenv("ADMIN_USER_IDS", "")
        playwright_timeout = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))
        default_credits = int(os.getenv("DEFAULT_CREDITS", "50"))
        stars_per_premium_day = int(os.getenv("STARS_PER_PREMIUM_DAY", "10"))
        bot_username = os.getenv("BOT_USERNAME", "HanimeBot")
        api_id = os.getenv("API_ID", "")
        api_hash = os.getenv("API_HASH", "")
        mongodb_uri = os.getenv("MONGODB_URI", "")
        owner_id = os.getenv("OWNER_ID", "")

        @property
        def admin_ids(self) -> Set[int]:
            if not self.admin_user_ids:
                return set()
            return {int(x.strip()) for x in self.admin_user_ids.split(",") if x.strip().isdigit()}

    config = FallbackSettings()
