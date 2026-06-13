import re
import logging
from uuid import uuid4
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from tgbot import db
from tgbot.services.scraper import URL_PATTERN
from tgbot.config import config

logger = logging.getLogger(__name__)

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline query search strings typed anywhere in Telegram chats."""
    inline_query = update.inline_query
    query = inline_query.query.strip()
    
    bot_username = context.bot.username or "HanimeBot"
    link_base = config.link_base_url or f"https://t.me/{bot_username}?start=lnk"
    
    results = []
    
    # Empty query: general hint
    if not query:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="🔍 Search Scraped Videos Index",
                description="Type keywords to search already processed titles...",
                input_message_content=InputTextMessageContent(
                    f"🎬 <b>Hanime Bot Curation</b>\n\nOpen @{bot_username} to request custom content scraping!",
                    parse_mode="HTML"
                )
            )
        )
        await inline_query.answer(results, cache_time=10, is_personal=True)
        return

    # Check Scenario A: Query matches plain Hanime TV URL
    if URL_PATTERN.match(query):
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="🎬 Scrape target video link ↗",
                description=f"Initiate scraping flow on: {query}",
                input_message_content=InputTextMessageContent(
                    f"/scrape {query}"
                )
            )
        )
        await inline_query.answer(results, cache_time=30)
        return

    # Check Scenario B: Database query by keyword title match
    try:
        # Search contents
        items = await db.fetch_all(
            "SELECT * FROM content WHERE title LIKE ? OR genres LIKE ? LIMIT 5",
            (f"%{query}%", f"%{query}%")
        )
        
        for item in items:
            title = item["title"]
            rating = item.get("rating", 8.0) or 8.0
            content_id = item["content_id"]
            slug = item["slug"]
            
            # Formulate the short link. Try to find if user has a short link for this content,
            # or fall back to standard deep link pattern: start=lnk_{slug}
            short_url = f"{link_base}_{slug}"
            
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"🎬 {title}",
                    description=f"⭐ {rating} | 🆔 Content ID: {content_id}",
                    input_message_content=InputTextMessageContent(
                        f"🎬 <b>{title}</b>\n"
                        f"🔗 {short_url}\n"
                        f"🆔 Content ID: <code>{content_id}</code>",
                        parse_mode="HTML"
                    )
                )
            )
            
        # Empty search results
        if not results:
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="❓ No results found!",
                    description="No scraped titles match. Click to prompt a raw scrape:",
                    input_message_content=InputTextMessageContent(
                        f"<b>Search query failed:</b> '{query}'\n\n"
                        f"💡 Try opening the bot and sending <code>/scrape [url]</code> to catalog new models!",
                        parse_mode="HTML"
                    )
                )
            )
    except Exception as ie:
        logger.error(f"Inline search failed miserably: {ie}")
        
    await inline_query.answer(results, cache_time=30)
