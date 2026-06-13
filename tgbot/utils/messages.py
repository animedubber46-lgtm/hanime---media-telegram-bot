# HTML Format Templates for Telegram Messages

WELCOME_NEW = (
    "👋 <b>Welcome to Hanime Scraper Bot!</b>\n\n"
    "To access premium scraping, links, and rewards, please create a unique username.\n\n"
    "🔽 Click <b>Register</b> below to start!"
)

WELCOME_BACK = (
    "👋 <b>Welcome back, {username}!</b>\n\n"
    "🌐 <b>Tier:</b> {tier_badge}\n"
    "💰 <b>Credits:</b> {credits}\n"
    "👥 <b>Referrals:</b> {referrals_count} / 5\n\n"
    "Ready to scrape or manage your links? Use the menu below:"
)

HELP_TEXT = (
    "❓ <b>Available Commands:</b>\n\n"
    "🎬 <code>/scrape [url]</code> - Scrape stream from URL\n"
    "🔗 <code>/shorten [url]</code> - Shorten a custom destination URL\n"
    "📂 <code>/mylinks</code> - Retrieve user link catalog\n"
    "👥 <code>/ref</code> - Your referral links & code\n"
    "📊 <code>/refstats</code> - Progress toward Premium\n"
    "⭐ <code>/premium</code> - Upgrade user account limits\n"
    "🏠 <code>/start</code> - Show dashboard\n\n"
    "<b>Your Badge:</b> {tier_badge} | Credits: {credits}"
)

SCRAPE_RESULT = (
    "🎬 <b>{title}</b>\n"
    "⭐ Rating: <b>{rating}/10</b> | 🎭 {genres}\n\n"
    "📝 <i>{description}</i>\n\n"
    "🛡️ ID: <code>{content_id}</code>"
)

LINK_CREATED = (
    "✅ <b>Short Link Generated Successfully!</b>\n\n"
    "🔗 {short_url}\n"
    "📊 Clicks: <b>{clicks}</b>\n"
    "🛡️ Content ID: <code>{content_id}</code>"
)

TOKEN_LINK_CREATED = (
    "✅ <b>Premium Token Link Created!</b>\n\n"
    "🎟 <code>{token_url}</code>\n"
    "⏳ Expires: <b>{expiry}</b>\n"
    "🔢 Max Uses: <b>{max_uses}</b>\n"
    "🛡️ ID: <code>{content_id}</code>"
)

REFERRAL_PANEL = (
    "👥 <b>Your Referral System</b>\n\n"
    "Earn <b>{default_credits}</b> credits for every user that registers via your link & makes 1 scrape!\n"
    "🌟 <b>Milestone:</b> Get 30 Days Free Premium at 5 valid referrals!\n\n"
    "🔗 <b>Your Invite Link:</b>\n"
    "<code>{referral_link}</code>\n\n"
    "👥 Total Referrals: <b>{total}</b>\n"
    "✅ Rewarded: <b>{rewarded}</b>\n"
    "💰 Total Credits Earned: <b>{credits_earned}</b>"
)

PREMIUM_COMPARE = (
    "⭐ <b>Upgrade to PREMIUM Tier</b>\n\n"
    "Unlock high-frequency, unrestricted access to the bot:\n\n"
    "<code>Feature          | Free    | Premium</code>\n"
    "<code>-----------------+---------+---------</code>\n"
    "<code>Scrapes / day    | 20      | 500</code>\n"
    "<code>Links / day      | 10      | Unlim</code>\n"
    "<code>Token Links      | ❌      | ✅</code>\n"
    "<code>Custom Expiry    | ❌      | ✅</code>\n"
    "<code>API Rate Limit   | 30/min  | 200/min</code>\n"
    "<code>Priority Queue   | ❌      | ✅</code>\n\n"
    "<b>Cost:</b> {stars_cost} Telegram Stars OR {credits_cost} Credits per 30 Days."
)

PAYMENT_SUCCESS = (
    "🎉 <b>Premium Upgrade Activated!</b>\n\n"
    "Your account is now credited with ⭐ <b>Premium Tier</b> benefits for 30 days.\n"
    "Thank you for supporting this bot! Enjoy unlimited speed."
)

CREDIT_UPGRADE_SUCCESS = (
    "🎉 <b>Success! Premium Unlocked.</b>\n\n"
    "You have successfully redeemed {credits_spent} credits for 30 days of ⭐ <b>Premium Tier</b> access."
)

RATE_LIMITED = (
    "⚠️ <b>Rate Limit Reached</b>\n\n"
    "You are sending requests too quickly!\n"
    "Cooldown required: <b>{seconds}s</b> for your current tier {tier_badge}.\n\n"
    "🌟 Upgrade to Premium to lift most limits!"
)

ERROR_GENERIC = (
    "⚠️ <b>Something went wrong!</b>\n\n"
    "An internal error occurred. Please try again later or use /help to reset."
)

SCRAP_ERROR = (
    "❌ <b>Scraping Failed</b>\n\n"
    "We could not resolve this TV link. The site metadata structural schema may have updated, or the server is unresponsive. Check the URL!"
)
