import logging
import traceback
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    PreCheckoutQueryHandler,
    ConversationHandler,
    ChatMemberHandler,
    filters,
    ContextTypes
)
from tgbot.config import config
from tgbot import db

# Import Handlers
from tgbot.handlers.start import start_handler, help_handler
from tgbot.handlers.auth import ASK_USERNAME, start_registration, handle_username, cancel
from tgbot.handlers.scrape import scrape_handler
from tgbot.handlers.shortener import (
    shorten_command_handler, mylinks_handler, dellink_command_handler,
    shorten_ask_callback, start_token_link_creation, handle_token_uses,
    handle_token_expiry, cancel_token_creation, ASK_TOKEN_USES, ASK_TOKEN_EXPIRY,
    ASK_SHORTENER_URL, ASK_SHORTENER_API_TOKEN, shortner_command_handler,
    handle_shortener_url, handle_shortener_api_token
)
from tgbot.handlers.referral import referral_handler, refstats_handler
from tgbot.handlers.premium import (
    premium_handler, buy_stars_callback, buy_credits_callback,
    precheckout_handler, payment_success_handler
)
from tgbot.handlers.admin import (
    admin_handler, admin_stats_callback, ban_user_command, unban_user_command,
    grant_premium_command, grant_credits_command, user_info_command,
    admin_broadcast_intent_callback, handle_admin_broadcast_draft,
    admin_bc_filter_callback, admin_bc_confirm_callback, admin_bc_cancel_callback,
    grant_super_premium_command, set_limit_command
)
from tgbot.handlers.inline import inline_handler

# Get logger configurations
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application):
    """Callback run automatically at bootstrap to construct tables."""
    logger.info("Initializing database schemas via migrations...")
    await db.init()
    logger.info("Migrations successfully deployed.")

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Listens for channel updates, confirming admin permissions, and registering channels dynamically."""
    my_member = update.my_chat_member
    if not my_member:
        return
        
    chat = my_member.chat
    if chat.type not in ["channel", "supergroup"]:
        return
        
    new_status = my_member.new_chat_member.status
    from telegram import ChatMember
    if new_status == ChatMember.ADMINISTRATOR:
        user_id = my_member.from_user.id if my_member.from_user else None
        if not user_id:
            return
            
        channel_id = chat.id
        channel_name = chat.title or "Channel"
        
        # Save to SQLite & MongoDB
        from tgbot.services.channels import add_channel_for_user
        await add_channel_for_user(user_id, channel_id, channel_name)
        
        # Send a direct DM confirmation to the user who added it
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎁 <b>Success! I am now an Administrator in your channel:</b> <code>{channel_name}</code>\n\n"
                     f"• Channel ID: <code>{channel_id}</code>\n\n"
                     "You can now manage and auto-upload movie files to this channel!",
                parse_mode="HTML"
            )
        except Exception as msg_err:
            logger.warning(f"Could not deliver private notification to administrator {user_id}: {msg_err}")

async def handle_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    CentralCallback query router mapping callback data prefixes to operations.
    Data scheme matches: '{prefix}:{action}:{extra}'
    """
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback trigger: user={user_id} data={data}")
    
    # 1. Menu Routing
    if data.startswith("menu:"):
        action = data.split(":")[1]
        if action == "main" or action == "back":
            # Recompute and update to display root dashboard menu
            from tgbot.services.users import get_user
            from tgbot.services.referral import get_referral_stats
            from tgbot.utils.messages import WELCOME_BACK
            from tgbot.utils.keyboards import main_menu_kb
            
            user = await get_user(user_id)
            if user:
                stats = await get_referral_stats(user_id)
                tier_badge = "⭐ Premium" if user.get("tier") == "premium" else "🔓 Free"
                await query.edit_message_text(
                    WELCOME_BACK.format(
                        username=user.get("username", "Member"),
                        tier_badge=tier_badge,
                        credits=user.get("credits", 0),
                        referrals_count=stats.get("rewarded", 0)
                    ),
                    parse_mode="HTML",
                    reply_markup=main_menu_kb()
                )
        elif action == "scrape":
            await query.answer()
            await query.edit_message_text(
                "🎬 <b>Web scraper tool</b>\n\n"
                "Please type your request using the text inputs:\n"
                "• Send <code>/scrape https://hanime.tv/videos/hentai/slug-here</code>\n"
                "• Or paste the raw hanime link below directly:",
                parse_mode="HTML",
                reply_markup=back_menu_kb()
            )
        elif action == "referral":
            await referral_handler(update, context)
        elif action == "premium":
            await premium_handler(update, context)
        elif action == "help":
            await help_handler(update, context)
            
    # 2. Video direct files download processing (MTProto up to 2GB)
    elif data.startswith("getfile:"):
        parts = data.split(":")
        content_id = int(parts[1])
        access_type = parts[2]
        
        # Check daily limits for FREE accounts
        from tgbot.services.users import get_user
        from datetime import datetime, timedelta
        user = await get_user(user_id)
        
        is_p = user and (user.get("tier") in ["premium", "super_premium", "admin"] or user_id in config.admin_ids or str(user_id) == str(config.owner_id))
        
        if not is_p:
            from tgbot.services.channels import get_bot_setting
            limit_str = await get_bot_setting("free_limit_videos", "2")
            free_limit = int(limit_str)
            
            # Count scrapes and downloads in the last 24h
            day_ago = (datetime.utcnow() - timedelta(days=1)).isoformat()
            history_rows = await db.fetch_all("SELECT * FROM scrape_history WHERE user_id = ? AND scraped_at >= ?", (user_id, day_ago))
            
            if len(history_rows) >= free_limit:
                await query.answer(f"⚠️ Daily Free Tier limit ({free_limit} videos) exceeded! Upgrade to Premium or contact admins for more credits.", show_alert=True)
                return
                
        # Send interactive alerts to confirm task trigger
        await query.answer("🚀 Processing request: Compiling video sections... please wait and check chat for updates.", show_alert=True)
        
        progress_msg = await query.message.reply_text(
            "⏳ <b>Initiating Media Loader Core ...</b>\n"
            "We are downloading the HLS stream, remuxing segment packets losslessly, and preparing up to 2GB.\n"
            "<i>This normally takes a minute. Please stand by, do not close the chat...</i>",
            parse_mode="HTML"
        )
        
        # Load content info
        from tgbot.services.shortener import ContentIDManager
        content = await ContentIDManager.get_content(content_id)
        if not content or not content.get("master_url"):
            await progress_msg.edit_text("❌ <b>Media stream resolution failure. Master playlist address not resolved!</b>", parse_mode="HTML")
            return
            
        master_url = content["master_url"]
        slug = content["slug"]
        title = content["title"]
        rating = content.get("rating", 8)
        genres = content.get("genres", "Hentai")
        
        # Trigger Downloader
        from tgbot.services.downloader import download_video, pyrogram_send_video_up_to_2gb
        import os
        
        video_path = await download_video(master_url, slug)
        
        if not video_path or not os.path.exists(video_path) or os.getsize(video_path) == 0:
            await progress_msg.edit_text("❌ <b>Download compilation failed.</b> The remote server returned bad segments or timed out.", parse_mode="HTML")
            return
            
        await progress_msg.edit_text("🚀 <b>Uploading film file over MTProto up to 2GB... Please wait...</b>", parse_mode="HTML")
        
        caption_text = (
            f"🎬 <b>{title}</b>\n"
            f"⭐ Rating: {rating}/10 | 🎭 {genres}\n\n"
            "⚡ Video rendered losslessly in full quality and auto-uploaded up to 2GB via Telegram Client bypass!"
        )
        
        sent_id = await pyrogram_send_video_up_to_2gb(
            chat_id=user_id,
            video_path=video_path,
            caption=caption_text
        )
        
        if sent_id:
            await progress_msg.delete()
            # Register to scrape logs so daily free tier limit tracking works
            await db.execute("INSERT INTO scrape_history (user_id, content_id) VALUES (?, ?)", (user_id, content_id))
        else:
            await progress_msg.edit_text("❌ <b>Transmission pipeline error.</b> Failed of uploading file through Pyrogram client.", parse_mode="HTML")
            
        # Clean local file space
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Purged file buffer from memory space: {video_path}")
        except Exception as file_io_err:
            logger.error(f"Failed deleting temporary compiled file: {file_io_err}")

    # 2. Scraper Sub-items
    elif data.startswith("scrape:"):
        parts = data.split(":")
        action = parts[1]
        content_id = int(parts[2])
        
        from tgbot.services.shortener import ContentIDManager
        content = await ContentIDManager.get_content(content_id)
        
        if not content:
            await query.answer("❌ Error: Media content not found inside indexes!", show_alert=True)
            return

        if action == "stream":
            await query.answer("Stream URL generated!")
            # Send raw stream link
            master_url = content.get("master_url", "")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📺 <b>Copy stream URL direct buffer link:</b>\n\n<code>{master_url}</code>",
                parse_mode="HTML"
            )
        elif action == "download":
            await query.answer("Preparing metadata packet ...")
            title = content.get("title", "")
            rating = content.get("rating", 8.0)
            genres = content.get("genres", "")
            desc = content.get("description", "")
            m3u = content.get("master_url", "")
            
            payload = (
                f"📥 <b>DOWNLOAD INFORMATION PACKET</b>\n\n"
                f"🏷 <b>Title:</b> {title}\n"
                f"⭐ <b>Rating:</b> {rating}/10\n"
                f"🎭 <b>Tags:</b> {genres}\n"
                f"📝 <b>Synopsis:</b>\n<i>{desc}</i>\n\n"
                f"📡 <b>HLS M3U8 feed stream:</b>\n<code>{m3u}</code>"
            )
            await context.bot.send_message(chat_id=user_id, text=payload, parse_mode="HTML")
            
        elif action == "re":
            # Re-scrapes - simplified captions refresh
            await query.answer("🔄 Refreshing dynamic ratings and statistics...")
            # Toggle edit captions to confirm update
            caption_text = (
                f"🎬 <b>{content['title']}</b> [REFRESHED]\n"
                f"⭐ Rating: <b>{content['rating']}/10</b> | 🎭 {content['genres']}\n\n"
                f"📝 <i>{content['description']}</i>\n\n"
                f"🛡️ ID: <code>{content['content_id']}</code>"
            )
            from tgbot.utils.keyboards import scrape_result_kb
            try:
                await query.edit_message_caption(
                    caption=caption_text,
                    parse_mode="HTML",
                    reply_markup=scrape_result_kb(content_id)
                )
            except Exception:
                # Text fallback
                await query.edit_message_text(
                    caption_text,
                    parse_mode="HTML",
                    reply_markup=scrape_result_kb(content_id)
                )

    # 3. Shortener callback triggers
    elif data.startswith("shorten:"):
        parts = data.split(":")
        sub = parts[1]
        
        if sub == "ask":
            await shorten_ask_callback(update, context)
        elif sub == "normal":
            # Instantly shortens mapping content to loop links
            content_id = int(parts[2])
            from tgbot.services.shortener import ContentIDManager, create_normal
            content = await ContentIDManager.get_content(content_id)
            if content:
                # Resolve destination
                bot_uname = context.bot.username or "HanimeBot"
                deep_long = f"https://t.me/{bot_uname}?start=stream_{content_id}"
                slug = await create_normal(deep_long, user_id, content_id=content_id)
                
                # Render Short link card
                from tgbot.utils.keyboards import created_link_kb
                from tgbot.utils.messages import LINK_CREATED
                
                link_base = config.link_base_url or f"https://t.me/{bot_uname}?start=lnk"
                short_url = f"{link_base}_{slug}"
                
                await query.edit_message_text(
                    LINK_CREATED.format(
                        short_url=short_url,
                        clicks=0,
                        content_id=content_id
                    ),
                    parse_mode="HTML",
                    reply_markup=created_link_kb(slug)
                )
            else:
                await query.answer("Content failed to load.", show_alert=True)

    # 4. Link Deletions / click logs
    elif data.startswith("link:"):
        parts = data.split(":")
        operation = parts[1]
        slug = parts[2]
        
        from tgbot.services.shortener import delete_link, delete_token, get_link_stats, get_token_stats
        
        if operation == "delete":
            deleted = await delete_link(slug, user_id)
            if deleted:
                await query.answer("✅ Short Link Deleted successfully!", show_alert=True)
                await query.edit_message_text("✅ <b>Short Link deleted successfully from index.</b>", parse_mode="HTML", reply_markup=back_menu_kb())
            else:
                await query.answer("❌ Error: Could not delete link.", show_alert=True)
                
        elif operation == "revoke":
            deleted = await delete_token(slug, user_id)
            if deleted:
                await query.answer("✅ Token Link Revoked!", show_alert=True)
                await query.edit_message_text("✅ <b>Token link successfully of status Revoked.</b>", parse_mode="HTML", reply_markup=back_menu_kb())
            else:
                await query.answer("❌ Error: Could not revoke token.", show_alert=True)
                
        elif operation == "stats":
            await query.answer()
            # Fetch normal stats
            stats = await get_link_stats(slug)
            if not stats:
                stats = await get_token_stats(slug)
                
            if not stats:
                await query.edit_message_text("❌ <b>Link statistics record not found.</b>", parse_mode="HTML", reply_markup=back_menu_kb())
                return
                
            is_tok = "token" in stats
            clicks = stats.get("uses" if is_tok else "clicks", 0)
            limit = stats.get("max_uses", "N/A") if is_tok else "Unlimited"
            expires = stats.get("expires_at") or "Permanent"
            
            stats_view = (
                f"📊 <b>Link Access Statistics</b>\n\n"
                f"🏷 <b>Key Slug:</b> <code>{slug}</code>\n"
                f"🔗 <b>Link Type:</b> {'Token Link (Premium)' if is_tok else 'Normal short link'}\n"
                f"📊 <b>Visits Count:</b> <b>{clicks}</b>\n"
                f"🔢 <b>Limit Uses:</b> <b>{limit}</b>\n"
                f"⏳ <b>Expiries:</b> <code>{expires}</code>\n"
                f"🛡️ <b>Content ID:</b> <code>{stats.get('content_id', 'Custom')}</code>"
            )
            await query.edit_message_text(stats_view, parse_mode="HTML", reply_markup=back_menu_kb())

    # 5. Admin Callback triggers
    elif data.startswith("admin:"):
        parts = data.split(":")
        sub = parts[1]
        
        if user_id not in config.admin_ids:
            await query.answer("🚫 Unauthorized access!", show_alert=True)
            return

        if sub == "stats":
            await admin_stats_callback(update, context)
        elif sub == "userlist":
            # Quick user list dump
            await query.answer()
            users = await get_all_users(limit=10)
            row_repr = []
            for u in users:
                tier = "⭐" if u["tier"] == "premium" else "🔓"
                row_repr.append(f"• <code>{u['user_id']}</code>: @{u['username']} {tier} Credits: {u['credits']}")
            body = "\n".join(row_repr) if row_repr else "Empty"
            await query.edit_message_text(f"👥 <b>Latest 10 registered profiles:</b>\n\n{body}", parse_mode="HTML", reply_markup=back_menu_kb())
        elif sub == "broadcast":
            await admin_broadcast_intent_callback(update, context)
        elif sub == "bc_filter":
            await admin_bc_filter_callback(update, context)
        elif sub == "bc_confirm":
            await admin_bc_confirm_callback(update, context)
        elif sub == "bc_cancel":
            await admin_bc_cancel_callback(update, context)
        elif sub == "banflow":
            await query.answer()
            await query.edit_message_text(
                "🚫 <b>To ban or unban users:</b>\n\n"
                "Please send the standard command shortcuts inside admin chats:\n"
                "• <code>/ban [user_id]</code> - blocks user from any queries\n"
                "• <code>/unban [user_id]</code> - restores user profiles",
                parse_mode="HTML",
                reply_markup=back_menu_kb()
            )
        elif sub == "grant":
            target = parts[2]
            await query.answer()
            await query.edit_message_text(
                f"⭐ <b>To grant {target} resources:</b>\n\n"
                f"Please issue these exact commands in admin chat:\n"
                f"• Granting Premium days:\n<code>/grantpremium [user_id] [days]</code>\n"
                f"• Granting Credits:\n<code>/grantcredits [user_id] [amount]</code>",
                parse_mode="HTML",
                reply_markup=back_menu_kb()
            )

    # 6. Referral Subs
    elif data.startswith("ref:"):
        action = data.split(":")[1]
        if action == "stats":
            await refstats_handler(update, context)

    # 7. Payments
    elif data.startswith("buy:"):
        action = data.split(":")[1]
        if action == "stars":
            await buy_stars_callback(update, context)
        elif action == "credits":
            await buy_credits_callback(update, context)

    elif data == "register_flow":
        # Safe trigger of auth registration flow via callback
        await start_registration(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback capture router handling general platform and scrape failures."""
    logger.error("Exception handled during update orchestration:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    logger.error(tb_string)
    
    # Notify user elegantly
    if isinstance(update, Update) and update.effective_message:
        err_msg = "⚠️ <b>An unexpected processing error occurred!</b>\n\nPlease try again or use /help to restart."
        if "playwright" in tb_string.lower() or "scrape" in tb_string.lower():
            err_msg = "❌ <b>Web scraping resolving failed!</b>\ntgbot could not finalize page loads. The server is either throttling us or URL is dead."
        try:
            await update.effective_message.reply_text(err_msg, parse_mode="HTML")
        except Exception:
            pass

def main():
    """Bot initialization launcher program."""
    if not config.bot_token or config.bot_token == "MY_BOT_TOKEN":
        print("CRITICAL: BOT_TOKEN environment variable is not set! Aborting bot boot.")
        return

    app = (
        ApplicationBuilder()
        .token(config.bot_token)
        .post_init(post_init)
        .build()
    )

    # ConversationHandler for User profile registration
    app.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("start", start_handler),
            CallbackQueryHandler(start_registration, pattern="^register_flow$")
        ],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_username)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
        name="user_registration_conv"
    ))

    # ConversationHandler for Premium Token Links custom creation variables
    app.add_handler(ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_token_link_creation, pattern=r"^shorten:token:\d+$")
        ],
        states={
            ASK_TOKEN_USES: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_token_uses)],
            ASK_TOKEN_EXPIRY: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_token_expiry)]
        },
        fallbacks=[CommandHandler("cancel", cancel_token_creation)],
        per_user=True,
        per_chat=True,
        name="premium_token_creation_conv"
    ))

    # ConversationHandler for Super Premium Custom URL Shorteners Config
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("shortner", shortner_command_handler)],
        states={
            ASK_SHORTENER_URL: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_shortener_url)],
            ASK_SHORTENER_API_TOKEN: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_shortener_api_token)]
        },
        fallbacks=[CommandHandler("cancel", cancel_token_creation)],
        per_user=True,
        per_chat=True,
        name="super_premium_shortener_conv"
    ))

    # Listen for administrator invitations inside user channels
    app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    # Core commands
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("scrape", scrape_handler))
    app.add_handler(CommandHandler("shorten", shorten_command_handler))
    app.add_handler(CommandHandler("mylinks", mylinks_handler))
    app.add_handler(CommandHandler("dellink", dellink_command_handler))
    app.add_handler(CommandHandler("ref", referral_handler))
    app.add_handler(CommandHandler("refstats", refstats_handler))
    app.add_handler(CommandHandler("premium", premium_handler))
    app.add_handler(CommandHandler("admin", admin_handler))

    # User Management Admin specific Commands
    app.add_handler(CommandHandler("ban", ban_user_command))
    app.add_handler(CommandHandler("unban", unban_user_command))
    app.add_handler(CommandHandler("grantpremium", grant_premium_command))
    app.add_handler(CommandHandler("grantsuperpremium", grant_super_premium_command))
    app.add_handler(CommandHandler("grantcredits", grant_credits_command))
    app.add_handler(CommandHandler("userinfo", user_info_command))
    app.add_handler(CommandHandler("setlimit", set_limit_command))

    # URL auto-detect on basic typing contains hanime schema
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"https?://hanime\.tv/videos/hentai/[\w-]+") & (~filters.COMMAND),
        scrape_handler
    ))
    
    # Message draft capturing for admin broadcasts
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & (~filters.COMMAND),
        handle_admin_broadcast_draft
    ))

    # Callback Button routers
    app.add_handler(CallbackQueryHandler(handle_callback_router))

    # Inline mode resolver
    app.add_handler(InlineQueryHandler(inline_handler))

    # Stars payment processors
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payment_success_handler))

    # Error handling
    app.add_error_handler(error_handler)

    print(f"Bot successfully launched, polling updates... (Username: @{config.bot_username})")
    
    # Run loop
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
