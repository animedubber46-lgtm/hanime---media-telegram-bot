import logging
from telegram import Update
from telegram.ext import ContextTypes
from tgbot.services.referral import get_referral_stats, get_referred_list
from tgbot.services.users import get_user
from tgbot.utils.keyboards import referral_kb, back_menu_kb
from tgbot.utils.messages import REFERRAL_PANEL
from tgbot.config import config
from tgbot.utils.decorators import require_registered

logger = logging.getLogger(__name__)

@require_registered
async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the user's primary referral system landing panel."""
    user_id = update.effective_user.id
    bot_uname = context.bot.username or "HanimeBot"
    
    # 1. Fetch referral statistics
    stats = await get_referral_stats(user_id)
    
    # 2. Build unique invitation deep-link
    referral_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"
    
    # 3. Format message and render inline keys
    caption_text = REFERRAL_PANEL.format(
        default_credits=config.default_credits,
        referral_link=referral_link,
        total=stats["total"],
        rewarded=stats["rewarded"],
        credits_earned=stats["credits_earned"]
    )
    
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(caption_text, parse_mode="HTML", reply_markup=referral_kb(bot_uname, str(user_id)))
    else:
        await update.message.reply_text(caption_text, parse_mode="HTML", reply_markup=referral_kb(bot_uname, str(user_id)))

@require_registered
async def refstats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders detailed referral tables with progress milestones."""
    user_id = update.effective_user.id
    
    # 1. Fetch stats and list of all joins
    ref_list = await get_referred_list(user_id)
    stats = await get_referral_stats(user_id)
    
    rewarded_clicks = stats["rewarded"]
    
    # 2. Build Milestone progress bar (5 referrals target)
    progress_val = min(5, rewarded_clicks)
    filled_blocks = "█" * progress_val
    empty_blocks = "░" * (5 - progress_val)
    progress_bar = f"{filled_blocks}{empty_blocks} {progress_val}/5 referrals"
    
    # 3. Build masked joins index table
    table_rows = []
    for ref in ref_list:
        raw_uname = ref.get("username")
        if not raw_uname:
            masked_name = "User_Anon"
        elif len(raw_uname) <= 3:
            masked_name = raw_uname + "***"
        else:
            masked_name = f"{raw_uname[:2]}***{raw_uname[-1:]}"
            
        status_label = "✅ Rewarded" if ref["rewarded"] == 1 else "⏳ Pending Scrape"
        table_rows.append(f"• <b>@{masked_name}</b>: {status_label}")
        
    table_text = "\n".join(table_rows) if table_rows else "<i>No user invitations recorded on your link yet.</i>"
    
    stats_msg = (
        "📊 <b>Detailed Referral Analytics</b>\n\n"
        f"👑 <b>Progression to Premium:</b>\n"
        f"<code>[{progress_bar}]</code>\n"
        "<i>Unlock 30-Day ⭐ Premium automatically when bar hits 5/5!</i>\n\n"
        f"💰 Credits earned from referrals: <b>{stats['credits_earned']}</b>\n\n"
        f"📋 <b>Invited Members List:</b>\n"
        f"{table_text}"
    )
    
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(stats_msg, parse_mode="HTML", reply_markup=back_menu_kb())
    else:
        await update.message.reply_text(stats_msg, parse_mode="HTML", reply_markup=back_menu_kb())

