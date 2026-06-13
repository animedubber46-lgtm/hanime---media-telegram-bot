import logging
from typing import Optional, Dict, Any, List
from tgbot import db
from tgbot.config import config
from tgbot import services

logger = logging.getLogger(__name__)

async def get_referral_stats(user_id: int) -> Dict[str, Any]:
    """Retrieves high-level referral figures for a specific referrer."""
    # Count total entries created
    total_row = await db.fetch_one("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ?", (user_id,))
    total = total_row["cnt"] if total_row else 0
    
    # Count fully rewarded/valid scrapes activations
    rewarded_row = await db.fetch_one("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ? AND rewarded = 1", (user_id,))
    rewarded = rewarded_row["cnt"] if rewarded_row else 0
    
    # Calculate earned sum
    credits_earned = rewarded * config.default_credits
    
    return {
        "total": total,
        "rewarded": rewarded,
        "credits_earned": credits_earned
    }

async def get_referred_list(referrer_id: int) -> List[Dict[str, Any]]:
    """Gathers username masked list of registrations acquired via invite."""
    return await db.fetch_all(
        """
        SELECT r.rewarded, r.created_at, u.username 
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
        """,
        (referrer_id,)
    )

async def check_and_grant_reward(referred_id: int) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether the user was referred and completes reward payouts
    upon their first active operation (called when first scrape finishes).
    
    Returns:
        A notification bundle dict if paid out, otherwise None.
    """
    # 1. Look up user record
    user = await db.fetch_one("SELECT referred_by, username FROM users WHERE user_id = ?", (referred_id,))
    if not user or not user.get("referred_by"):
        return None
        
    referrer_id = user["referred_by"]
    referred_username = user["username"] or f"ID {referred_id}"
    
    # 2. Check if a referrals row already exists and is rewarded
    existing = await db.fetch_one(
        "SELECT id, rewarded FROM referrals WHERE referred_id = ?", 
        (referred_id,)
    )
    
    if existing:
        if existing["rewarded"] == 1:
            # Already paid
            return None
        else:
            # Register exists but unpaid, update to rewarded
            await db.execute("UPDATE referrals SET rewarded = 1 WHERE referred_id = ?", (referred_id,))
    else:
        # Create new rewarded entry
        await db.execute(
            "INSERT INTO referrals (referrer_id, referred_id, rewarded) VALUES (?, ?, 1)",
            (referrer_id, referred_id)
        )
        
    # 3. Pay credits to referrer
    credits_reward = config.default_credits
    await db.execute(
        "UPDATE users SET credits = credits + ? WHERE user_id = ?",
        (credits_reward, referrer_id)
    )
    
    # 4. Check milesone status
    stats = await get_referral_stats(referrer_id)
    rewarded_total = stats["rewarded"]
    
    premium_unlocked = False
    # If they hit exactly 5 physical valid active signups, upgrade them automatically to 30 days premium!
    if rewarded_total == 5:
        from tgbot.services.users import grant_premium
        await grant_premium(referrer_id, days=30)
        premium_unlocked = True
        logger.info(f"Referrer {referrer_id} unlocked 30-day Premium for milestone: {rewarded_total} referrals.")
        
    return {
        "referrer_id": referrer_id,
        "referred_username": referred_username,
        "credits_added": credits_reward,
        "premium_unlocked": premium_unlocked,
        "total_rewarded": rewarded_total
    }

async def register_pending_referral(referred_id: int, referrer_id: int) -> bool:
    """Invoked during user creation stage to mark deep-links prior to registration completion."""
    if referred_id == referrer_id:
        return False
        
    # Check if this node has been already indexed inside systems
    existing_user = await db.fetch_one("SELECT 1 FROM users WHERE user_id = ?", (referred_id,))
    if existing_user:
        return False # Only new joins count towards referrals
        
    # Check if referral is already logged
    existing_ref = await db.fetch_one("SELECT 1 FROM referrals WHERE referred_id = ?", (referred_id,))
    if existing_ref:
        return False
        
    await db.execute(
        "INSERT OR IGNORE INTO referrals (referrer_id, referred_id, rewarded) VALUES (?, ?, 0)",
        (referrer_id, referred_id)
    )
    return True
