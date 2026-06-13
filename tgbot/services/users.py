from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, List
from tgbot import db
from tgbot.config import config

logger = logging.getLogger(__name__)

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches the user's database entry.
    Self-heals and downgrades premium tiers automatically if they have expired.
    """
    user = await db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not user:
        return None
        
    # Self-heal expired subscription status
    if user.get("tier") == "premium" and user.get("premium_until"):
        try:
            # Handle possible varied types (str format)
            expiry_str = user["premium_until"]
            # Clean possible trailing format errors
            if " " in expiry_str:
                expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            else:
                expiry_dt = datetime.fromisoformat(expiry_str)
                
            if datetime.now() > expiry_dt:
                # Downgrade immediately
                await db.execute(
                    "UPDATE users SET tier = 'free', premium_until = NULL WHERE user_id = ?",
                    (user_id,)
                )
                user["tier"] = "free"
                user["premium_until"] = None
                logger.info(f"Self-healed: User {user_id} reverted to free tier due to expiration.")
        except Exception as e:
            logger.error(f"Error self-healing user premium state: {e}")
            
    return user

async def create_user(user_id: int, username: str, referred_by: Optional[int] = None) -> Dict[str, Any]:
    """Inserts a new user record into the system and returns it."""
    # Ensure referred_by is not self
    if referred_by and referred_by == user_id:
        referred_by = None
        
    await db.execute(
        """
        INSERT OR IGNORE INTO users (user_id, username, credits, referred_by)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, username, config.default_credits, referred_by)
    )
    
    # Return user
    user = await get_user(user_id)
    return user

async def is_username_unique(username: str, exclude_user_id: Optional[int] = None) -> bool:
    """Checks if a username is already taken."""
    if exclude_user_id:
        row = await db.fetch_one(
            "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?) AND user_id != ?",
            (username, exclude_user_id)
        )
    else:
        row = await db.fetch_one(
            "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
    return row is None

async def ban_user(user_id: int, is_ban: bool = True) -> bool:
    """Bans or unbans a user in the database."""
    val = 1 if is_ban else 0
    rows = await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (val, user_id))
    return rows > 0

async def grant_premium(user_id: int, days: int = 30) -> bool:
    """Extends or activates user Premium privileges for a set number of days."""
    user = await get_user(user_id)
    if not user:
        return False
        
    now = datetime.now()
    if user.get("tier") == "premium" and user.get("premium_until"):
        # Extend existing
        try:
            current_expiry = datetime.fromisoformat(user["premium_until"])
        except ValueError:
            current_expiry = datetime.strptime(user["premium_until"], "%Y-%m-%d %H:%M:%S")
            
        new_expiry = max(current_expiry, now) + timedelta(days=days)
    else:
        # Start fresh
        new_expiry = now + timedelta(days=days)
        
    rows = await db.execute(
        "UPDATE users SET tier = 'premium', premium_until = ? WHERE user_id = ?",
        (new_expiry.isoformat(), user_id)
    )
    return rows > 0

async def grant_credits(user_id: int, amount: int) -> bool:
    """Adds a positive or negative amount of credits to the user's account."""
    rows = await db.execute(
        "UPDATE users SET credits = max(0, credits + ?) WHERE user_id = ?",
        (amount, user_id)
    )
    return rows > 0

async def deduct_credits(user_id: int, amount: int) -> bool:
    """Deducts credits, returning False if credits are insufficient."""
    user = await get_user(user_id)
    if not user or user.get("credits", 0) < amount:
        return False
        
    rows = await db.execute(
        "UPDATE users SET credits = credits - ? WHERE user_id = ?",
        (amount, user_id)
    )
    return rows > 0

async def get_all_users(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Gets a paginated list of all users."""
    return await db.fetch_all("SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))

async def get_premium_users_count() -> int:
    """Counts active premium subscribers."""
    now = datetime.now().isoformat()
    row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM users WHERE tier = 'premium' AND premium_until > ?",
        (now,)
    )
    return row["cnt"] if row else 0
