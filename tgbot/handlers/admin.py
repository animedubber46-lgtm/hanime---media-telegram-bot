import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from tgbot import db
from tgbot.services.users import get_user, ban_user, grant_premium, grant_credits, get_all_users, get_premium_users_count
from tgbot.services.shortener import get_total_links_count, ContentIDManager
from tgbot.utils.decorators import admin_only
from tgbot.utils.keyboards import admin_panel_kb, back_menu_kb
from tgbot.config import config

logger = logging.getLogger(__name__)

@admin_only
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renders the main administrative backend dashboard keys."""
    await update.message.reply_text(
        "🛠 <b>Bot Admin Command Suite</b>\n\n"
        "Welcome Creator. Use the button dashboard below to pull real database analytics, "
        "propagate custom push broadcast letters, or configure limits on member profiles:",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )

@admin_only
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Computes and renders granular database analytics from real table figures."""
    query = update.callback_query
    await query.answer()
    
    # 1. Users calculations
    try:
        users_tot = await db.fetch_one("SELECT COUNT(*) as cnt FROM users")
        total_users = users_tot["cnt"] if users_tot else 0
        
        premium_users = await get_premium_users_count()
        
        # Scrapes logs analytics
        scrapes_today_row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM scrape_history WHERE scraped_at >= date('now', 'start of day')"
        )
        scrapes_today = scrapes_today_row["cnt"] if scrapes_today_row else 0
        
        scrapes_week_row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM scrape_history WHERE scraped_at >= date('now', '-7 days')"
        )
        scrapes_week = scrapes_week_row["cnt"] if scrapes_week_row else 0
        
        scrapes_all_row = await db.fetch_one("SELECT COUNT(*) as cnt FROM scrape_history")
        scrapes_all = scrapes_all_row["cnt"] if scrapes_all_row else 0
        
        # Short links
        total_links = await get_total_links_count()
        
        # Top 5 most searched media
        top_scrapes = await ContentIDManager.get_top_scrapes(5)
        top_table = []
        for i, val in enumerate(top_scrapes):
            title = val.get("title", "Unknown")
            hits = val.get("hit_count", 0)
            cid = val.get("content_id", 0)
            top_table.append(f"{i+1}. <code>#{cid}</code> {title[:30]} - <b>{hits} hits</b>")
            
        top_text = "\n".join(top_table) if top_table else "No media scrapes indexed yet."
        
        stats_text = (
            "📊 <b>System Statistics & Metrics</b>\n\n"
            f"👥 <b>Userbase metrics:</b>\n"
            f"• Total users: <b>{total_users}</b>\n"
            f"• Premium users: <b>{premium_users}</b>\n\n"
            f"🎬 <b>Scraper volumetric:</b>\n"
            f"• Processed today: <b>{scrapes_today}</b>\n"
            f"• Processed this week: <b>{scrapes_week}</b>\n"
            f"• Processed total: <b>{scrapes_all}</b>\n\n"
            f"🔗 <b>Link Shortener count:</b>\n"
            f"• Active short URLs: <b>{total_links}</b>\n\n"
            f"🔥 <b>Top 5 Media Hits:</b>\n"
            f"{top_text}"
        )
        await query.edit_message_text(stats_text, parse_mode="HTML", reply_markup=back_menu_kb())
    except Exception as stat_err:
        logger.error(f"Failed loading stats data: {stat_err}")
        await query.edit_message_text(f"❌ Failed to fetch telemetry figures: {stat_err}", reply_markup=back_menu_kb())

# --------------------------------------------------------------------------
# Quick Admin command shortcut bindings
# --------------------------------------------------------------------------

@admin_only
async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kicks and blocks a user from using the bot in SQLite database."""
    if not context.args:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/ban [user_id]</code>", parse_mode="HTML")
        return
        
    try:
        target_id = int(context.args[0])
        success = await ban_user(target_id, is_ban=True)
        if success:
            await update.message.reply_text(f"✅ <b>User {target_id} successfully Banned.</b>", parse_mode="HTML")
            # Try to push notice
            try:
                await context.bot.send_message(target_id, "🚫 <b>You have been banned from this service by the main administrator.</b>", parse_mode="HTML")
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ Failure. User profile not found inside the database.", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ target_id parameter must be a valid integer number.", parse_mode="HTML")

@admin_only
async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restores database block status for a member."""
    if not context.args:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/unban [user_id]</code>", parse_mode="HTML")
        return
        
    try:
        target_id = int(context.args[0])
        success = await ban_user(target_id, is_ban=False)
        if success:
            await update.message.reply_text(f"✅ <b>User {target_id} restored successfully.</b>", parse_mode="HTML")
            try:
                await context.bot.send_message(target_id, "🔔 <b>Your access to the scraper service has been successfully restored!</b> Welcome back.", parse_mode="HTML")
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ User profile not found inside database.", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ target_id parameters must be a valid integer.", parse_mode="HTML")

@admin_only
async def grant_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds premium days to user."""
    if len(context.args) < 1:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/grantpremium [user_id] [days]</code>", parse_mode="HTML")
        return
        
    try:
        tgt_id = int(context.args[0])
        days = int(context.args[1]) if len(context.args) > 1 else 30
        
        worked = await grant_premium(tgt_id, days)
        if worked:
            await update.message.reply_text(f"✅ <b>Granted {days} Premium days to {tgt_id}.</b>", parse_mode="HTML")
            try:
                await context.bot.send_message(tgt_id, f"🌟 <b>An administrator rewarded your account with {days} Days of Premium benefits!</b> Enjoy high speeds.", parse_mode="HTML")
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ Could not update user. Ensure they are registered first.", parse_mode="HTML")
    except Exception as ge:
        await update.message.reply_text(f"❌ Error during grant execution: {ge}", parse_mode="HTML")

@admin_only
async def grant_credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Augments user credit balances."""
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/grantcredits [user_id] [amount]</code>", parse_mode="HTML")
        return
        
    try:
        tgt_id = int(context.args[0])
        amt = int(context.args[1])
        
        done = await grant_credits(tgt_id, amt)
        if done:
            await update.message.reply_text(f"✅ <b>Credited {amt} credits to User {tgt_id}.</b>", parse_mode="HTML")
            try:
                await context.bot.send_message(tgt_id, f"💰 <b>An admin has credited your wallet with +{amt} credits!</b>", parse_mode="HTML")
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ Failure. Ensure target user is registered in the DB first.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}", parse_mode="HTML")

@admin_only
async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieves full profile details of a member."""
    if not context.args:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/userinfo [user_id]</code>", parse_mode="HTML")
        return
        
    try:
        tgt_id = int(context.args[0])
        user = await get_user(tgt_id)
        if not user:
            await update.message.reply_text("❌ User profile not found inside the systems.", parse_mode="HTML")
            return
            
        stats_text = (
            "👤 <b>Member Record Check</b>\n\n"
            f"• User ID: <code>{user['user_id']}</code>\n"
            f"• Username: <b>@{user['username']}</b>\n"
            f"• Tier: <b>{user['tier'].upper()}</b>\n"
            f"• Premium Until: <code>{user['premium_until'] or 'N/A'}</code>\n"
            f"• Wallets credits: <b>{user['credits']}</b>\n"
            f"• Referred By: <code>{user['referred_by'] or 'Direct'}</code>\n"
            f"• Banned marker: <b>{'YES' if user['banned'] == 1 else 'NO'}</b>\n"
            f"• Joined date: <code>{user['created_at']}</code>"
        )
        await update.message.reply_text(stats_text, parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Parameter must be a valid integer ID.", parse_mode="HTML")

# --------------------------------------------------------------------------
# Broadcast Logic Flows
# --------------------------------------------------------------------------

@admin_only
async def admin_broadcast_intent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiates broadcast draft sequence by requesting custom HTML draft text."""
    query = update.callback_query
    await query.answer()
    
    # Store flag that admin wants to broadcast next plain message.
    context.user_data["waiting_for_broadcast_text"] = True
    
    await query.edit_message_text(
        "📢 <b>Broadcast Creation Suite</b>\n\n"
        "Please reply to this text with the message draft you wish to broadcast to members.\n"
        "• Standard telegram HTML formatting tags are supported.\n"
        "• Reply with <code>cancel</code> to cancel.",
        parse_mode="HTML"
    )

async def handle_admin_broadcast_draft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Validates the draft message and sets target filtering layers."""
    if not context.user_data.get("waiting_for_broadcast_text"):
        return
        
    text = update.message.text.strip()
    if text.lower() == "cancel":
        context.user_data.pop("waiting_for_broadcast_text", None)
        await update.message.reply_text("❌ Broadcast sequence cancelled.")
        return
        
    # Store draft
    context.user_data["broadcast_draft"] = text
    context.user_data.pop("waiting_for_broadcast_text", None)
    
    # Show filters keyboard
    filter_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Broadcast to All", callback_data="admin:bc_filter:all"),
            InlineKeyboardButton("⭐ Premium Only", callback_data="admin:bc_filter:premium")
        ],
        [
            InlineKeyboardButton("🔓 Free Users Only", callback_data="admin:bc_filter:free")
        ],
        [
            InlineKeyboardButton("❌ Discard Draft", callback_data="admin:bc_cancel")
        ]
    ])
    
    await update.message.reply_text(
        "📢 <b>Broadcast Filter Configuration</b>\n\n"
        "Draft saved successfully. Select who should receive this push notification:\n\n"
        f"<b>Draft Content:</b>\n<i>{text}</i>",
        parse_mode="HTML",
        reply_markup=filter_kb
    )

async def admin_bc_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calculates user demographics, offering preview confirmation keys."""
    query = update.callback_query
    await query.answer()
    
    # admin:bc_filter:xxxx
    parts = query.data.split(":")
    filter_type = parts[2]
    
    # Count targets
    count = 0
    now = datetime.now().isoformat()
    if filter_type == "all":
        row = await db.fetch_one("SELECT COUNT(*) as cnt FROM users")
        count = row["cnt"] if row else 0
    elif filter_type == "premium":
        row = await db.fetch_one("SELECT COUNT(*) as cnt FROM users WHERE tier = 'premium' AND premium_until > ?", (now,))
        count = row["cnt"] if row else 0
    elif filter_type == "free":
        row = await db.fetch_one("SELECT COUNT(*) as cnt FROM users WHERE tier = 'free' OR premium_until IS NULL OR premium_until <= ?", (now,))
        count = row["cnt"] if row else 0
        
    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm & Broadcast", callback_data=f"admin:bc_confirm:{filter_type}"),
            InlineKeyboardButton("❌ Abort", callback_data="admin:bc_cancel")
        ]
    ])
    
    await query.edit_message_text(
        f"📢 <b>Ready to Push Dispatch!</b>\n\n"
        f"• Filter audience: <b>{filter_type.upper()}</b>\n"
        f"• Destination count: <b>{count} users</b>\n\n"
        f"Confirming will broadcast the message immediately! Spacing delay: 50ms/user.",
        parse_mode="HTML",
        reply_markup=confirm_kb
    )

async def admin_bc_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs broadcast push loops synchronously, mapping stats back to admin."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    filter_type = parts[3]
    
    draft = context.user_data.get("broadcast_draft")
    if not draft:
        await query.edit_message_text("❌ Draft not found! Start again via /admin.", reply_markup=back_menu_kb())
        return
        
    await query.edit_message_text("🚀 <b>Broadcasting, please wait...</b>", parse_mode="HTML")
    
    # Query targets
    now = datetime.now().isoformat()
    if filter_type == "all":
        targets = await db.fetch_all("SELECT user_id FROM users")
    elif filter_type == "premium":
        targets = await db.fetch_all("SELECT user_id FROM users WHERE tier = 'premium' AND premium_until > ?", (now,))
    else: # free
        targets = await db.fetch_all("SELECT user_id FROM users WHERE tier = 'free' OR premium_until IS NULL OR premium_until <= ?", (now,))
        
    success_cnt = 0
    failed_cnt = 0
    
    # Spawn sequential looping tasks
    for tgt in targets:
        tid = tgt["user_id"]
        try:
            await context.bot.send_message(
                chat_id=tid,
                text=draft,
                parse_mode="HTML"
            )
            success_cnt += 1
        except Exception:
            failed_cnt += 1
            
        # 50ms spacing to completely bypass Telegram Flood limit issues
        await asyncio.sleep(0.05)
        
    # Deliver diagnostic metrics back to administrator
    await query.message.reply_text(
        f"📢 <b>Broadcast stats summary complete:</b>\n\n"
        f"✅ Dispatched successfully: <b>{success_cnt} players</b>\n"
        f"❌ Failed/Blocked: <b>{failed_cnt} players</b>",
        parse_mode="HTML",
        reply_markup=back_menu_kb()
    )
    
    # Wipe draft
    context.user_data.pop("broadcast_draft", None)

async def admin_bc_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Discards existing drafts."""
    query = update.callback_query
    await query.answer("Broadcast discarded.", show_alert=True)
    context.user_data.pop("broadcast_draft", None)
    context.user_data.pop("waiting_for_broadcast_text", None)
    await query.edit_message_text(
        "🛠 Administrative commands discarded.",
        reply_markup=admin_panel_kb()
    )


@admin_only
async def grant_super_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grants Super Premium tier status to a user for channel uploads."""
    if len(context.args) < 1:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/grantsuperpremium [user_id] [days]</code>", parse_mode="HTML")
        return
        
    try:
        tgt_id = int(context.args[0])
        days = int(context.args[1]) if len(context.args) > 1 else 30
        
        from datetime import datetime, timedelta
        until_dt = datetime.now() + timedelta(days=days)
        until_str = until_dt.isoformat()
        
        await db.execute(
            "UPDATE users SET tier = 'super_premium', premium_until = ? WHERE user_id = ?",
            (until_str, tgt_id)
        )
        
        await update.message.reply_text(f"✅ <b>Granted {days} Super Premium days to account ID: {tgt_id}.</b>", parse_mode="HTML")
        try:
            await context.bot.send_message(
                tgt_id,
                f"🌟 <b>An administrator upgraded your tier to Super Premium for {days} Days!</b>\n\n"
                "You can now configure channel auto-uploads and custom API shorteners!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    except Exception as ge:
        await update.message.reply_text(f"❌ Error during grant execution: {ge}", parse_mode="HTML")


@admin_only
async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configures daily limits directly from the bot settings chat."""
    if not context.args:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/setlimit [number]</code>", parse_mode="HTML")
        return
        
    limit_str = context.args[0]
    if not limit_str.isdigit():
        await update.message.reply_text("❌ Daily limit must be a positive integer number (e.g. 2, 5, 10):", parse_mode="HTML")
        return
        
    from tgbot.services.channels import set_bot_setting
    await set_bot_setting("free_limit_videos", limit_str)
    
    await update.message.reply_text(
        f"✅ <b>Daily free download limit updated to {limit_str} videos per day!</b>",
        parse_mode="HTML"
    )
