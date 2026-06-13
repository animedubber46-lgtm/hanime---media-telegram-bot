from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from tgbot.config import config
from tgbot.utils.rate_limiter import rate_limiter
from tgbot.utils.messages import RATE_LIMITED, PREMIUM_COMPARE
from tgbot.utils.keyboards import premium_kb

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        if user_id not in config.admin_ids:
            # Silent return as per specifications
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def require_registered(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from tgbot.services.users import get_user
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        user = await get_user(user_id)
        
        if not user:
            # Let start handler handle registration conversation triggers
            text = (
                "👋 <b>Welcome!</b> You must be registered to perform this action.\n"
                "Please send /start to create your profile."
            )
            if update.callback_query:
                await update.callback_query.answer("⚠️ Register first!", show_alert=True)
                await update.callback_query.message.reply_text(text, parse_mode="HTML")
            elif update.message:
                await update.message.reply_text(text, parse_mode="HTML")
            return
            
        if user.get("banned"):
            msg = "🚫 <b>You are banned from using this bot.</b>"
            if update.callback_query:
                await update.callback_query.answer("🚫 Banned!", show_alert=True)
            elif update.message:
                await update.message.reply_text(msg, parse_mode="HTML")
            return
            
        return await func(update, context, *args, **kwargs)
    return wrapper

def require_premium(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from tgbot.services.users import get_user
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        user = await get_user(user_id)
        
        is_premium = user and user.get("tier") == "premium"
        if not is_premium:
            text = PREMIUM_COMPARE.format(
                stars_cost=config.stars_per_premium_day * 30,
                credits_cost=100
            )
            if update.callback_query:
                await update.callback_query.answer("⭐ Premium required!", show_alert=True)
                await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=premium_kb(config.stars_per_premium_day * 30, 100))
            elif update.message:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=premium_kb(config.stars_per_premium_day * 30, 100))
            return
            
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limited(action: str):
    """
    Decorator to apply flexible tier-based rates.
    For Scrape action:
      - Free: 20 scrapes/day, 1 scrape per 10s
      - Premium: 500 scrapes/day, 1 scrape per 2s
    For Shorten / action:
      - Free: 10 links/day
      - Premium: Unlimited links/day
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            from tgbot.services.users import get_user
            if not update.effective_user:
                return await func(update, context, *args, **kwargs)
                
            user_id = update.effective_user.id
            
            # Admins bypass all limits
            if user_id in config.admin_ids:
                return await func(update, context, *args, **kwargs)
                
            user = await get_user(user_id)
            tier = user.get("tier", "free") if user else "free"
            
            if action == "scrape":
                freq_limit = 1
                freq_window = 10 if tier == "free" else 2
                
                daily_limit = 20 if tier == "free" else 500
                daily_window = 86400  # 1 day
                
                # Check sliding window frequency limit
                if not rate_limiter.check(user_id, "scrape_freq", freq_limit, freq_window):
                    wait_time = int(rate_limiter.time_to_wait(user_id, "scrape_freq", freq_limit, freq_window))
                    badge = "🔓 Free" if tier == "free" else "⭐ Premium"
                    await update.effective_message.reply_text(
                        RATE_LIMITED.format(seconds=wait_time, tier_badge=badge),
                        parse_mode="HTML"
                    )
                    return
                
                # Check daily volumetric limit
                if not rate_limiter.check(user_id, "scrape_daily", daily_limit, daily_window):
                    badge = "🔓 Free" if tier == "free" else "⭐ Premium"
                    await update.effective_message.reply_text(
                        f"⚠️ <b>Daily Scrape Limit Exceeded!</b>\n\n"
                        f"Your tier {badge} allows maximum <b>{daily_limit}</b> scrapes every 24 hours.\n"
                        f"Consider upgrading to Premium for next-level bandwidth!",
                        parse_mode="HTML",
                        reply_markup=premium_kb(config.stars_per_premium_day * 30, 100)
                    )
                    return
                    
            elif action == "shorten":
                if tier == "free":
                    daily_limit = 10
                    daily_window = 86400
                    if not rate_limiter.check(user_id, "shorten_daily", daily_limit, daily_window):
                        await update.effective_message.reply_text(
                            "⚠️ <b>Daily Link Shortening Limit Reached!</b>\n\n"
                            "🔓 Free tier users can create up to 10 links per day. Upgrade to ⭐ Premium for unlimited link shortening!",
                            parse_mode="HTML",
                            reply_markup=premium_kb(config.stars_per_premium_day * 30, 100)
                        )
                        return
                        
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
