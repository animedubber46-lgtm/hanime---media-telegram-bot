import string
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from tgbot import db
from tgbot.config import config

logger = logging.getLogger(__name__)

def generate_random_code(length: int = 6) -> str:
    """Generates a secure, highly unique identifier string."""
    choices = string.ascii_letters + string.digits
    return "".join(random.choice(choices) for _ in range(length))

class ContentIDManager:
    @staticmethod
    async def get_or_create(slug: str, result: Dict[str, Any]) -> int:
        """
        Retrieves an index mapping for scraped content, or registers a new entry.
        Increments hit count on accesses.
        """
        # Search existing
        existing = await db.fetch_one("SELECT content_id FROM content WHERE slug = ?", (slug,))
        if existing:
            content_id = existing["content_id"]
            await db.execute("UPDATE content SET hit_count = hit_count + 1 WHERE content_id = ?", (content_id,))
            return content_id
            
        # Register new content
        title = result.get("title", "Unknown Title")
        desc = result.get("description", "")
        rating = result.get("rating", 8.0)
        genres = result.get("genres", "")
        thumb = result.get("thumbnail_url", "")
        master = result.get("master_url", "")
        
        await db.execute(
            """
            INSERT INTO content (slug, title, description, rating, genres, thumbnail_url, master_url, hit_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (slug, title, desc, rating, genres, thumb, master)
        )
        
        row = await db.fetch_one("SELECT content_id FROM content WHERE slug = ?", (slug,))
        return row["content_id"] if row else 1

    @staticmethod
    async def get_content(content_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves content metadata from its unique primary ID."""
        return await db.fetch_one("SELECT * FROM content WHERE content_id = ?", (content_id,))

    @staticmethod
    async def get_top_scrapes(limit: int = 5) -> List[Dict[str, Any]]:
        """Returns the top scraped videos based on hit frequencies."""
        return await db.fetch_all("SELECT * FROM content ORDER BY hit_count DESC LIMIT ?", (limit,))

async def create_normal(long_url: str, user_id: int, content_id: Optional[int] = None, expires_at: Optional[datetime] = None) -> str:
    """Creates a regular short link routing mapping and returns its unique slug."""
    for _ in range(10): # Trial loop to ensure db constraint safety
        slug = generate_random_code(6)
        existing = await db.fetch_one("SELECT 1 FROM short_links WHERE slug = ?", (slug,))
        if not existing:
            break
    else:
        slug = generate_random_code(8)
        
    expires_str = expires_at.isoformat() if expires_at else None
    
    await db.execute(
        """
        INSERT INTO short_links (slug, long_url, user_id, content_id, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (slug, long_url, user_id, content_id, expires_str)
    )
    return slug

async def create_token(content_id: int, user_id: int, max_uses: int = 0, expires_at: Optional[datetime] = None) -> str:
    """Creates a premium tokenized link access block and returns the unique token."""
    for _ in range(10):
        token = generate_random_code(10)
        existing = await db.fetch_one("SELECT 1 FROM token_links WHERE token = ?", (token,))
        if not existing:
            break
    else:
        token = generate_random_code(14)
        
    expires_str = expires_at.isoformat() if expires_at else None
    
    await db.execute(
        """
        INSERT INTO token_links (token, content_id, user_id, max_uses, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (token, content_id, user_id, max_uses, expires_str)
    )
    return token

async def get_link_stats(slug: str) -> Optional[Dict[str, Any]]:
    """Gathers clicks metadata and expiration status for a normal slug."""
    link = await db.fetch_one("SELECT * FROM short_links WHERE slug = ?", (slug,))
    if not link:
        return None
        
    # Check expiration
    is_expired = False
    if link.get("expires_at"):
        try:
            expires = datetime.fromisoformat(link["expires_at"])
            is_expired = datetime.now() > expires
        except Exception:
            pass
            
    return {
        "slug": slug,
        "long_url": link["long_url"],
        "user_id": link["user_id"],
        "clicks": link["clicks"],
        "is_expired": is_expired,
        "expires_at": link["expires_at"],
        "content_id": link["content_id"]
    }

async def get_token_stats(token: str) -> Optional[Dict[str, Any]]:
    """Gathers status and uses for a token link."""
    link = await db.fetch_one("SELECT * FROM token_links WHERE token = ?", (token,))
    if not link:
        return None
        
    is_expired = False
    if link.get("expires_at"):
        try:
            expires = datetime.fromisoformat(link["expires_at"])
            is_expired = datetime.now() > expires
        except Exception:
            pass
            
    is_exhausted = False
    max_uses = link.get("max_uses", 0)
    uses = link.get("uses", 0)
    if max_uses > 0 and uses >= max_uses:
        is_exhausted = True
        
    return {
        "token": token,
        "content_id": link["content_id"],
        "user_id": link["user_id"],
        "max_uses": max_uses,
        "uses": uses,
        "is_expired": is_expired,
        "is_exhausted": is_exhausted,
        "expires_at": link["expires_at"]
    }

async def delete_link(slug: str, user_id: int) -> bool:
    """Removes a normal short link."""
    rows = await db.execute("DELETE FROM short_links WHERE slug = ? AND user_id = ?", (slug, user_id))
    return rows > 0

async def delete_token(token: str, user_id: int) -> bool:
    """Revokes a premium token link."""
    rows = await db.execute("DELETE FROM token_links WHERE token = ? AND user_id = ?", (token, user_id))
    return rows > 0

async def record_click(slug: str) -> bool:
    """Registers click count incrementally for normal links."""
    rows = await db.execute("UPDATE short_links SET clicks = clicks + 1 WHERE slug = ?", (slug,))
    return rows > 0

async def record_token_use(token: str) -> bool:
    """Registers token utilization count."""
    rows = await db.execute("UPDATE token_links SET uses = uses + 1 WHERE token = ?", (token,))
    return rows > 0

async def get_links_paginated(user_id: int, limit: int = 5, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetches normal links created by user, sorted by date."""
    return await db.fetch_all(
        "SELECT slug, clicks, content_id, created_at, expires_at FROM short_links WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )

async def get_tokens_paginated(user_id: int, limit: int = 5, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetches premium token links generated by user, sorted by date."""
    return await db.fetch_all(
        "SELECT token, content_id, uses, max_uses, created_at FROM token_links WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )

async def get_total_links_count() -> int:
    """Returns absolute total shortened records count."""
    count_sl = await db.fetch_one("SELECT COUNT(*) as cnt FROM short_links")
    count_tl = await db.fetch_one("SELECT COUNT(*) as cnt FROM token_links")
    total = (count_sl["cnt"] if count_sl else 0) + (count_tl["cnt"] if count_tl else 0)
    return total

async def record_scrape_history(user_id: int, content_id: int):
    """Saves a scrape execution to user's log history."""
    await db.execute(
        "INSERT INTO scrape_history (user_id, content_id) VALUES (?, ?)",
        (user_id, content_id)
    )
    # Check limit constraint: maintain 20 entries log per user to prevent DB bloating
    history = await db.fetch_all("SELECT id FROM scrape_history WHERE user_id = ? ORDER BY scraped_at DESC", (user_id,))
    if len(history) > 20:
        old_ids = [row["id"] for row in history[20:]]
        placeholders = ",".join("?" for _ in old_ids)
        await db.execute(f"DELETE FROM scrape_history WHERE id IN ({placeholders})", tuple(old_ids))

async def get_scrape_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches video items previously processed by this user."""
    return await db.fetch_all(
        """
        SELECT c.*, h.scraped_at 
        FROM scrape_history h
        JOIN content c ON h.content_id = c.content_id
        WHERE h.user_id = ?
        ORDER BY h.scraped_at DESC
        LIMIT ?
        """,
        (user_id, limit)
    )
