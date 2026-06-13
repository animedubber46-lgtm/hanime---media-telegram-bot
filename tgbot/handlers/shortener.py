import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from tgbot.services.users import get_user
from tgbot.services.shortener import (
    create_normal, create_token, get_link_stats, get_token_stats,
    delete_link, delete_token, get_links_paginated, ContentIDManager
)
from tgbot.utils.keyboards import created_link_kb, mylinks_kb, shorten_type_kb
from tgbot.utils.decorators import require_registered, rate_limited
from tgbot.utils.messages import LINK_CREATED, TOKEN_LINK_CREATED
from tgbot.config import config

logger = logging.getLogger(__name__)

# Conversation states for creating custom Token Links
ASK_TOKEN_USES = 2
ASK_TOKEN_EXPIRY = 3
ASK_SHORTENER_URL = 4
ASK_SHORTENER_API_TOKEN = 5

@require_registered
@rate_limited("shorten")
async def shorten_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /shorten command to create instant normal links from any input URL."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Provide a target URL to shorten!</b>\n"
            "<b>Format:</b> <code>/shorten https://example.com/long-page</code>",
            parse_mode="HTML"
        )
        return
        
    long_url = context.args[0]
    user_id = update.effective_user.id
    
    # Check if this maps to a local content
    content_id = None
    if "/videos/hentai/" in long_url:
        from tgbot.services.scraper import extract_slug
        slug = extract_slug(long_url)
        content_id = await ContentIDManager.get_or_create(slug, {"title": slug.replace("-", " ").title()})

    slug = await create_normal(long_url, user_id, content_id=content_id)
    
    bot_uname = context.bot.username or "HanimeBot"
    link_base = config.link_base_url or f"https://t.me/{bot_uname}?start=lnk"
    short_url = f"{link_base}_{slug}"
    
    await update.message.reply_text(
        LINK_CREATED.format(
            short_url=short_url,
            clicks=0,
            content_id=content_id or "Custom"
        ),
        parse_mode="HTML",
        reply_markup=created_link_kb(slug)
    )

@require_registered
async def mylinks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists shortened links mapped to this user account with pagination."""
    user_id = update.effective_user.id
    
    # Retrieve current page (default: 0)
    page = 0
    query = update.callback_query
    if query:
        await query.answer()
        parts = query.data.split(":")
        if len(parts) >= 3:
            page = int(parts[2])
            
    limit = 5
    offset = page * limit
    
    # Query user links
    links = await get_links_paginated(user_id, limit=limit, offset=offset)
    
    # Check if there's a next page available
    next_links = await get_links_paginated(user_id, limit=1, offset=offset + limit)
    has_next = len(next_links) > 0
    
    if not links and page == 0:
        empty_text = "📂 <b>You don't have any shortened links yet!</b>\n\nUse /scrape or /shorten to create one."
        if query:
            await query.edit_message_text(empty_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="menu:main")]]))
        else:
            await update.message.reply_text(empty_text, parse_mode="HTML")
        return
        
    nav_markup = mylinks_kb(links, page, has_next)
    text = f"📂 <b>Your Links Index (Page {page+1})</b>\n\nClick on any link below to view click logs and deletion triggers:"
    
    if query:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=nav_markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=nav_markup)

@require_registered
async def dellink_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles explicit deletion requests for custom shortened links."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/dellink [link_slug]</code>",
            parse_mode="HTML"
        )
        return
        
    slug = context.args[0]
    user_id = update.effective_user.id
    
    deleted = await delete_link(slug, user_id)
    if deleted:
        await update.message.reply_text("✅ <b>Short link successfully deleted!</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ <b>Link not found or unauthorized deletion request.</b>", parse_mode="HTML")


# --------------------------------------------------------------------------
# Conversation Handlers for Token Links Custom Configurations (Uses & Expiry)
# --------------------------------------------------------------------------

async def shorten_ask_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Intercepts callback and asks which shortener method to construct."""
    query = update.callback_query
    await query.answer()
    
    # Format: shorten:ask:{content_id}
    parts = query.data.split(":")
    content_id = int(parts[2])
    
    user_id = update.effective_user.id
    user = await get_user(user_id)
    is_premium = user and user.get("tier") == "premium"
    
    await query.edit_message_text(
        "🚀 <b>Link Generation Options</b>\n\n"
        "<b>🔗 Normal Link:</b> Creates an un-throttled shortened url. Open for multiple uses.\n"
        "<b>🎟 Token Link:</b> Highly configurable, restricted-entry link. Multi-use caps, token values, security shields (⭐ Premium Only).",
        parse_mode="HTML",
        reply_markup=shorten_type_kb(content_id, is_premium)
    )

async def start_token_link_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Begins state flow requesting token parameter entries."""
    query = update.callback_query
    await query.answer()
    
    # Format: shorten:token:{content_id}
    parts = query.data.split(":")
    content_id = int(parts[2])
    
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    # Check subscription bounds before launching conversation states
    if not user or user.get("tier") != "premium":
        await query.answer("⭐ Premium account tier required!", show_alert=True)
        return ConversationHandler.END
        
    context.user_data["token_content_id"] = content_id
    
    await query.edit_message_text(
        "🎟 <b>Token Link Configuration (Step 1/2)</b>\n\n"
        "Send the <b>maximum number of uses</b> allowed for this link:\n"
        "• Type <code>1</code> for single-use access\n"
        "• Type <code>0</code> for unlimited usage",
        parse_mode="HTML"
    )
    return ASK_TOKEN_USES

async def handle_token_uses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validates the maximum uses integer constraint."""
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Please enter a positive integer number (e.g. 0, 1, 5, 100):")
        return ASK_TOKEN_USES
        
    context.user_data["token_uses"] = int(text)
    
    await update.message.reply_text(
        "🎟 <b>Token Link Expiration (Step 2/2)</b>\n\n"
        "Define when this token collapses/expires. Send one of the options below:\n"
        "• <code>24h</code> for 24 hours duration\n"
        "• <code>7d</code> for 7 days duration\n"
        "• <code>never</code> for permanent validity status",
        parse_mode="HTML"
    )
    return ASK_TOKEN_EXPIRY

async def handle_token_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses and computes expiration window and inserts the Token record."""
    input_str = update.message.text.strip().lower()
    
    expires_at = None
    if input_str == "24h":
        expires_at = datetime.now() + timedelta(hours=24)
    elif input_str == "7d":
        expires_at = datetime.now() + timedelta(days=7)
    elif input_str == "never":
        expires_at = None
    else:
        await update.message.reply_text("❌ Invalid format! Please type <code>24h</code>, <code>7d</code>, or <code>never</code>:", parse_mode="HTML")
        return ASK_TOKEN_EXPIRY
        
    content_id = context.user_data.get("token_content_id")
    max_uses = context.user_data.get("token_uses", 0)
    user_id = update.effective_user.id
    
    # Create the token record
    token_slug = await create_token(
        content_id=content_id,
        user_id=user_id,
        max_uses=max_uses,
        expires_at=expires_at
    )
    
    bot_uname = context.bot.username or "HanimeBot"
    token_url = f"https://t.me/{bot_uname}?start=tok_{token_slug}"
    
    # Notify user of completion
    await update.message.reply_text(
        TOKEN_LINK_CREATED.format(
            token_url=token_url,
            expiry=input_str.upper() if expires_at else "NEVER",
            max_uses=max_uses if max_uses > 0 else "UNLIMITED",
            content_id=content_id
        ),
        parse_mode="HTML",
        reply_markup=created_link_kb(token_slug, is_token=True)
    )
    
    # Clear conversation cache
    context.user_data.pop("token_content_id", None)
    context.user_data.pop("token_uses", None)
    return ConversationHandler.END

async def cancel_token_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Emergency cancel handler during token generation steps."""
    await update.message.reply_text("❌ Token link generation aborted.")
    return ConversationHandler.END


@require_registered
async def shortner_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Begins custom shortener configuration conversation for Super Premium users (allows GPLinks, etc.)."""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    # Check Super Premium bounds
    is_super = user and (user.get("tier") in ["super_premium", "admin"] or user_id in config.admin_ids or str(user_id) == str(config.owner_id))
    if not is_super:
        await update.message.reply_text(
            "⭐ <b>Super Premium Feature Required!</b>\n\n"
            "This custom shortener or channel auto-upload feature is restricted to <b>Super Premium</b> accounts.\n"
            "Please contact the Owner to upgrade your subscription.",
            parse_mode="HTML"
        )
        return ConversationHandler.END
        
    await update.message.reply_text(
        "🔗 <b>Configure Custom Shortener (Step 1/2)</b>\n\n"
        "Please send your shortener website API base URL.\n"
        "<b>Format example:</b> <code>https://gplinks.in/api</code>\n\n"
        "Type /cancel to abort at any time.",
        parse_mode="HTML"
    )
    return ASK_SHORTENER_URL

async def handle_shortener_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores shortener URL and moves to API token state."""
    url = update.message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("❌ Invalid format! API URL must start with http:// or https://. Please enter again:")
        return ASK_SHORTENER_URL
        
    context.user_data["shortener_url"] = url
    await update.message.reply_text(
        "🔑 <b>Configure Custom Shortener (Step 2/2)</b>\n\n"
        "Please send your shortener API key or security token:",
        parse_mode="HTML"
    )
    return ASK_SHORTENER_API_TOKEN

async def handle_shortener_api_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Completes and persists the user shortener configuration."""
    token = update.message.text.strip()
    url = context.user_data.get("shortener_url")
    user_id = update.effective_user.id
    
    from tgbot.services.channels import add_shortener_for_user
    await add_shortener_for_user(user_id, url, token)
    
    await update.message.reply_text(
        "✅ <b>Custom Shortener Configured!</b>\n\n"
        f"🌐 <b>API URL:</b> <code>{url}</code>\n"
        f"🔑 <b>API Token:</b> <code>{token[:4]}****</code>\n\n"
        "This shortener is now linked and will automatically monetize the free buttons in your channel auto-posts!",
        parse_mode="HTML"
    )
    
    # Clean user state cache
    context.user_data.pop("shortener_url", None)
    return ConversationHandler.END
