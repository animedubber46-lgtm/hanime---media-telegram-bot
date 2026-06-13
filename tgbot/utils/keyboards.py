from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_kb() -> InlineKeyboardMarkup:
    """Builds the primary dashboard menu."""
    keyboard = [
        [
            InlineKeyboardButton("🎬 Scrape", callback_data="menu:scrape"),
            InlineKeyboardButton("🔗 My Links", callback_data="page:links:0")
        ],
        [
            InlineKeyboardButton("👥 Referral", callback_data="menu:referral"),
            InlineKeyboardButton("⭐ Premium", callback_data="menu:premium")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu:help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_menu_kb() -> InlineKeyboardMarkup:
    """Standard menu return button."""
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]]
    return InlineKeyboardMarkup(keyboard)

def scrape_result_kb(content_id: int) -> InlineKeyboardMarkup:
    """Actions performed on scraped video content."""
    keyboard = [
        [
            InlineKeyboardButton("📋 Copy Stream URL", callback_data=f"scrape:stream:{content_id}"),
            InlineKeyboardButton("🔗 Shorten Link", callback_data=f"shorten:ask:{content_id}")
        ],
        [
            InlineKeyboardButton("📥 Download Info", callback_data=f"scrape:download:{content_id}"),
            InlineKeyboardButton("🔄 Re-scrape", callback_data=f"scrape:re:{content_id}")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def shorten_type_kb(content_id: int, is_premium: bool) -> InlineKeyboardMarkup:
    """Shortener options selection keyboard."""
    token_label = "🎟 Token Link (Premium)" if is_premium else "🎟 Token Link (⭐ Premium Only)"
    keyboard = [
        [
            InlineKeyboardButton("🔗 Normal Link", callback_data=f"shorten:normal:{content_id}"),
            InlineKeyboardButton(token_label, callback_data=f"shorten:token:{content_id}")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def created_link_kb(slug: str, is_token: bool = False) -> InlineKeyboardMarkup:
    """Actions after a shortlink has been established."""
    action = "revoke" if is_token else "delete"
    keyboard = [
        [
            InlineKeyboardButton("🗑 Delete/Revoke Link", callback_data=f"link:{action}:{slug}"),
            InlineKeyboardButton("📊 Clicks Stats", callback_data=f"link:stats:{slug}")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def mylinks_kb(links: list, page: int, has_next: bool) -> InlineKeyboardMarkup:
    """Paginated user link index."""
    keyboard = []
    # Index items
    for link in links:
        slug = link.get("slug")
        clicks = link.get("clicks", 0)
        is_token = "token" in link
        prefix = "🎟" if is_token else "🔗"
        keyboard.append([
            InlineKeyboardButton(f"{prefix} {slug} ({clicks} clicks)", callback_data=f"link:stats:{slug}")
        ])
    
    # Navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀ Prev", callback_data=f"page:links:{page-1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton("Next ▶", callback_data=f"page:links:{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(keyboard)

def referral_kb(bot_username: str, referral_code: str) -> InlineKeyboardMarkup:
    """Referrals panel keys."""
    share_url = f"https://t.me/{bot_username}?start={referral_code}"
    tg_share_link = f"https://t.me/share/url?url={share_url}&text=Unlock%20unlimited%20premium%20streaming%20and%20scraping!"
    keyboard = [
        [
            InlineKeyboardButton("🔗 Send to Friends", url=tg_share_link),
            InlineKeyboardButton("📊 Detailed Stats", callback_data="ref:stats")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def premium_kb(stars_cost: int, credits_cost: int) -> InlineKeyboardMarkup:
    """Premium tier buy options."""
    keyboard = [
        [
            InlineKeyboardButton(f"⭐ Buy with Stars ({stars_cost} XTR)", callback_data="buy:stars"),
            InlineKeyboardButton(f"💰 Use {credits_cost} Credits", callback_data="buy:credits")
        ],
        [
            InlineKeyboardButton("👥 Earn Free via Referrals", callback_data="menu:referral")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_panel_kb() -> InlineKeyboardMarkup:
    """Command center options for administrators."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Bot Stats", callback_data="admin:stats"),
            InlineKeyboardButton("👥 User List", callback_data="admin:userlist")
        ],
        [
            InlineKeyboardButton("📢 Broadcast Message", callback_data="admin:broadcast"),
            InlineKeyboardButton("🚫 Ban/Unban User", callback_data="admin:banflow")
        ],
        [
            InlineKeyboardButton("⭐ Grant Premium", callback_data=f"admin:grant:premium"),
            InlineKeyboardButton("💰 Grant Credits", callback_data=f"admin:grant:credits")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
