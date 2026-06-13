import re
import logging
from telegram import Update
from telegram.ext import ContextTypes
from tgbot.services.scraper import resolve, extract_slug, ScrapError
from tgbot.services.tmdb import get_metadata
from tgbot.services.shortener import ContentIDManager, record_scrape_history
from tgbot.services.users import get_user
from tgbot.services.referral import check_and_grant_reward
from tgbot.utils.decorators import require_registered, rate_limited
from tgbot.utils.keyboards import scrape_result_kb, shorten_type_kb
from tgbot.utils.messages import SCRAPE_RESULT, SCRAP_ERROR

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://hanime\.tv/videos/hentai/[\w-]+")

@require_registered
@rate_limited("scrape")
async def scrape_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /scrape command and automatic URL copy-pastes."""
    user_id = update.effective_user.id
    
    # 1. Fetch search URL
    url = ""
    if update.message:
        if context.args:
            url = context.args[0]
        else:
            # Check if message text matches the pattern directly
            url = update.message.text.strip()
    
    # 2. Check URL validity
    if not url or not URL_PATTERN.match(url):
        error_text = (
            "⚠️ <b>Invalid Scrape Target!</b>\n\n"
            "Please provide a valid hanime.tv URL.\n"
            "<b>Format:</b> <code>/scrape https://hanime.tv/videos/hentai/slug-name</code>"
        )
        if update.message:
            await update.message.reply_text(error_text, parse_mode="HTML")
        return

    # 3. Notify user and start processing
    status_msg = await update.effective_message.reply_text(
        "⏳ <b>Parsing video URL ...</b>", parse_mode="HTML"
    )
    
    slug = extract_slug(url)
    
    try:
        # 4. Update status and call resolver asynchronously
        await status_msg.edit_text("⏳ <b>Bypassing security layers ...</b>", parse_mode="HTML")
        result = await resolve(url)
        
        # 5. Enrich description & rating using TMDB API
        await status_msg.edit_text("⏳ <b>Fetching TMDB metadata ...</b>", parse_mode="HTML")
        tmdb_data = await get_metadata(result.title, slug)
        
        description = result.description
        rating = result.rating
        genres = result.genres
        thumbnail_url = result.thumbnail_url
        
        if tmdb_data:
            if tmdb_data.get("description"):
                description = tmdb_data["description"]
            if tmdb_data.get("rating"):
                rating = tmdb_data["rating"]
            if tmdb_data.get("genres"):
                genres = tmdb_data["genres"]
            if tmdb_data.get("poster_url"):
                thumbnail_url = tmdb_data["poster_url"]

        # Ensure description is compact (max 200 chars)
        if len(description) > 200:
            description = f"{description[:197]}..."
            
        # 6. Save or fetch from Content DB
        content_id = await ContentIDManager.get_or_create(
            slug=slug,
            result={
                "title": result.title,
                "description": description,
                "rating": rating,
                "genres": genres,
                "thumbnail_url": thumbnail_url,
                "master_url": result.master_url
            }
        )
        
        # Log to scrape history
        await record_scrape_history(user_id, content_id)
        
        # Check Super Premium channels auto posting trigger!
        user_info = await get_user(user_id)
        if user_info and (user_info.get("tier") in ["super_premium", "admin"] or user_id in config.admin_ids or str(user_id) == str(config.owner_id)):
            from tgbot.services.channels import get_user_channels, get_user_shortener, shorten_url_via_custom_shortener
            channels = await get_user_channels(user_id)
            if channels:
                bot_uname = context.bot.username or "HanimeScraperBot"
                long_prem_url = f"https://t.me/{bot_uname}?start=file_{content_id}_premium"
                long_free_url = f"https://t.me/{bot_uname}?start=file_{content_id}_free"
                
                # Fetch custom shortener settings
                shortener = await get_user_shortener(user_id)
                short_free_url = long_free_url
                if shortener:
                    api_url = shortener.get("api_url")
                    api_token = shortener.get("api_token")
                    shortened = await shorten_url_via_custom_shortener(api_url, api_token, long_free_url)
                    if shortened:
                        short_free_url = shortened
                
                # Construct buttons
                chan_kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("👑 Premium (Direct)", url=long_prem_url),
                        InlineKeyboardButton("📺 Watch / Download (Free)", url=short_free_url)
                    ]
                ])
                
                chan_caption = (
                    f"🎬 <b>{result.title}</b>\n"
                    f"⭐ Rating: <b>{rating}/10</b> | 🎭 {genres}\n\n"
                    f"📝 <i>{description}</i>\n\n"
                    "📥 Click buttons below to stream or download this episode:"
                )
                
                for chan in channels:
                    try:
                        await context.bot.send_photo(
                            chat_id=chan["channel_id"],
                            photo=thumbnail_url,
                            caption=chan_caption,
                            parse_mode="HTML",
                            reply_markup=chan_kb
                        )
                        logger.info(f"Broadcasted auto-post to channel {chan['channel_name']} successfully.")
                    except Exception as chan_err:
                        logger.error(f"Failed broadcasting to channel {chan['channel_id']}: {chan_err}")

        # 7. Check and grant referral rewards upon their first scrape
        try:
            reward_bundle = await check_and_grant_reward(user_id)
            if reward_bundle:
                referrer_id = reward_bundle["referrer_id"]
                ref_uname = reward_bundle["referred_username"]
                credits_got = reward_bundle["credits_added"]
                
                push_text = f"🎉 <b>@{ref_uname}</b> joined via your link & did their first scrape!\n➕ <b>+{credits_got}</b> credits added to your profile."
                if reward_bundle.get("premium_unlocked"):
                    push_text += "\n\n🌟 <b>Congratulations!</b> You've unlocked 30 Days Free Premium Tier for reaching 5 valid referrals!"
                    
                # Deliver real-time push notification to the referrer
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=push_text,
                    parse_mode="HTML"
                )
        except Exception as ref_err:
            logger.error(f"Failed handling referral trigger: {ref_err}")

        # Delete status message
        await status_msg.delete()
        
        # 8. Render result card with photo representation & inline menu
        caption_text = SCRAPE_RESULT.format(
            title=result.title,
            rating=rating,
            genres=genres,
            description=description,
            content_id=content_id
        )
        
        # If thumbnail_url is invalid or fails, send clean message instead of crash
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=thumbnail_url,
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=scrape_result_kb(content_id)
            )
        except Exception as photo_err:
            logger.warning(f"Could not send photo card: {photo_err}. Sending as rich text.")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🎬 <b>{result.title}</b>\n\n📌 <b>Poster Url:</b> {thumbnail_url}\n\n" + caption_text,
                parse_mode="HTML",
                reply_markup=scrape_result_kb(content_id)
            )
            
    except ScrapError as se:
        await status_msg.edit_text(f"❌ Scraping failed: <i>{se}</i>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"General scraper handler error: {e}")
        await status_msg.edit_text(SCRAP_ERROR, parse_mode="HTML")
