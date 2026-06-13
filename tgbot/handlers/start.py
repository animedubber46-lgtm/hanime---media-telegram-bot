import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from tgbot.services.users import get_user
from tgbot.services.referral import get_referral_stats
from tgbot.utils.messages import WELCOME_NEW, WELCOME_BACK, HELP_TEXT
from tgbot.utils.keyboards import main_menu_kb, back_menu_kb

logger = logging.getLogger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrypoint command for start, routing new and existing registrations and deep-links."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # 1. Parse deep-link parameters for invite code tracking or video file serving
    start_arg = ""
    if context.args:
        start_arg = context.args[0]
        # Invitation referral tracking
        referrer_str = start_arg.lower().replace("ref_", "").replace("start_", "")
        if referrer_str.isdigit():
            referrer_id = int(referrer_str)
            if referrer_id != user_id:
                context.user_data["pending_ref"] = referrer_id
                logger.info(f"Silently cached pending referral from {referrer_id} for user {user_id}")

    # 2. Check if the user is in our database
    user = await get_user(user_id)
    
    if not user:
        # Prompt Registration
        reg_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Register Account", callback_data="register_flow")]
        ])
        await update.message.reply_text(
            WELCOME_NEW,
            parse_mode="HTML",
            reply_markup=reg_keyboard
        )
        return ConversationHandler.END

    # 3. Handle Banned state
    if user.get("banned"):
        await update.message.reply_text("🚫 <b>You have been banned from using this bot.</b>", parse_mode="HTML")
        return ConversationHandler.END

    # 4. Handle Video deep link files (Super Premium auto post channel redirects)
    if start_arg and start_arg.lower().startswith("file_"):
        parts = start_arg.split("_")
        if len(parts) >= 3:
            try:
                content_id = int(parts[1])
                access_type = parts[2].lower()
                
                from tgbot.services.shortener import ContentIDManager
                content = await ContentIDManager.get_content(content_id)
                if not content:
                    await update.message.reply_text("❌ <b>Media content file record not found in system index.</b>", parse_mode="HTML")
                    return ConversationHandler.END
                    
                title = content.get("title", "Scraped Video")
                rating = content.get("rating", 8.2)
                genres = content.get("genres", "Hentai")
                desc = content.get("description", "")
                
                # Formulate custom download keyboards
                if access_type == "premium":
                    is_p = user.get("tier") in ["premium", "super_premium", "admin"] or user_id in config.admin_ids or str(user_id) == str(config.owner_id)
                    if not is_p:
                        await update.message.reply_text(
                            f"🎬 <b>{title} (Premium Video Locked)</b>\n\n"
                            "👑 High-speed direct uploads up to 2GB are exclusive to <b>Premium Members</b>.\n\n"
                            "Please contact the owner / administrators to upgrade, or use the free Shortener option to solve inside Telegram channels!",
                            parse_mode="HTML"
                        )
                        return ConversationHandler.END
                        
                    kb = InlineKeyboardMarkup([[
                        InlineKeyboardButton("⚡ Get Premium Video File (2GB MTProto)", callback_data=f"getfile:{content_id}:premium")
                    ]])
                else:
                    kb = InlineKeyboardMarkup([[
                        InlineKeyboardButton("📥 Download Free Video File", callback_data=f"getfile:{content_id}:free")
                    ]])
                    
                caption = (
                    f"🎬 <b>{title}</b>\n"
                    f"⭐ Rating: <b>{rating}/10</b> | 🎭 {genres}\n\n"
                    f"📝 <i>{desc}</i>\n\n"
                    "👉 Click the button below to initiate high-speed rendering of your video file direct to this chat:"
                )
                
                try:
                    await update.message.reply_photo(
                        photo=content.get("thumbnail_url"),
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=kb
                    )
                except Exception:
                    await update.message.reply_text(
                        caption,
                        parse_mode="HTML",
                        reply_markup=kb
                    )
                return ConversationHandler.END
            except Exception as deep_err:
                logger.error(f"Error serving deep-link file redirection: {deep_err}")

    # 5. User exists - Display Main Menu Dashboard
    ref_stats = await get_referral_stats(user_id)
    tier_badge = "⭐ Premium" if user.get("tier") == "premium" else "🔓 Free"
    if user.get("tier") == "super_premium":
        tier_badge = "🌟 Super Premium"
    
    await update.message.reply_text(
        WELCOME_BACK.format(
            username=user.get("username", username or "Member"),
            tier_badge=tier_badge,
            credits=user.get("credits", 0),
            referrals_count=ref_stats.get("rewarded", 0)
        ),
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )
    return ConversationHandler.END

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the bot command handbook."""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    tier_badge = "🔓 Unknown"
    credits_amt = 0
    if user:
        tier_badge = "⭐ Premium" if user.get("tier") == "premium" else "🔓 Free"
        credits_amt = user.get("credits", 0)
        
    await update.message.reply_text(
        HELP_TEXT.format(tier_badge=tier_badge, credits=credits_amt),
        parse_mode="HTML",
        reply_markup=back_menu_kb()
    )
