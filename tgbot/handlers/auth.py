import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from tgbot.services.users import create_user, is_username_unique, get_user
from tgbot.services.referral import register_pending_referral
from tgbot.utils.messages import WELCOME_BACK
from tgbot.utils.keyboards import main_menu_kb

ASK_USERNAME = 1

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Begins the registration ConversationHandler state machine."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "✍️ <b>Profile Registration</b>\n\n"
            "Please choose a unique username.\n"
            "• Length: 3-20 characters\n"
            "• Allowed chars: letters, numbers, and underscores\n\n"
            "📝 Reply with your desired username:",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "✍️ <b>Profile Registration</b>\n\n"
            "Please reply to this message with your desired username (3-20 characters, letters, numbers, underscores only):",
            parse_mode="HTML"
        )
    return ASK_USERNAME

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validates the username input and builds user profile."""
    username = update.message.text.strip()
    user_id = update.effective_user.id
    
    # 1. Validation regex
    pattern = r"^[a-zA-Z0-9_]{3,20}$"
    if not re.match(pattern, username):
        await update.message.reply_text(
            "❌ <b>Invalid Username format!</b>\n\n"
            "Must be between 3 and 20 characters and contain only letters, numbers, or underscores.\n\n"
            "✍️ Please type a different username:",
            parse_mode="HTML"
        )
        return ASK_USERNAME
        
    # 2. Check uniqueness in SQLite db
    unique = await is_username_unique(username)
    if not unique:
        await update.message.reply_text(
            "❌ <b>Username is already taken!</b>\n\n"
            "Please choose a different, unique name:",
            parse_mode="HTML"
        )
        return ASK_USERNAME
        
    # 3. Apply referral links of start context if pending
    pending_ref_referrer = context.user_data.get("pending_ref")
    referred_by_id = None
    if pending_ref_referrer and pending_ref_referrer != user_id:
        referred_by_id = pending_ref_referrer
        # Pre-log raw relationship structure
        await register_pending_referral(user_id, pending_ref_referrer)
        
    # 4. Create user record
    await create_user(user_id=user_id, username=username, referred_by=referred_by_id)
    
    await update.message.reply_text(
        f"🎉 <b>Registration Complete!</b>\n"
        f"Welcome aboard, <b>@{username}</b>. You have been credited with 50 default credits!\n\n",
        parse_mode="HTML"
    )
    
    # Display main dashboard directly
    badge = "🔓 Free"
    await update.message.reply_text(
        WELCOME_BACK.format(
            username=username,
            tier_badge=badge,
            credits=50,
            referrals_count=0
        ),
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )
    
    # Clean cache
    context.user_data.pop("pending_ref", None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the registration flow."""
    await update.message.reply_text("❌ Registration cancelled. Use /start to register whenever you are ready.")
    return ConversationHandler.END
