import os
import aiosqlite
import asyncio
import logging
import pymongo
from typing import Optional, Dict, Any, List
from datetime import datetime
from tgbot.config import config

logger = logging.getLogger(__name__)
db_path = config.database_path

mongo_client: Optional[pymongo.MongoClient] = None
mongo_db = None

def get_mongo_db():
    global mongo_client, mongo_db
    if mongo_client is None and config.mongodb_uri:
        try:
            mongo_client = pymongo.MongoClient(config.mongodb_uri)
            mongo_db = mongo_client.get_database("hanime_bot_db")
            logger.info("Connected successfully to MongoDB Atlas database.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB URI defined: {e}")
    return mongo_db

async def init():
    """Run SQLite database tables setup and pull data from MongoDB if available."""
    async with aiosqlite.connect(db_path) as db:
        # Create Users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                tier TEXT DEFAULT 'free',
                premium_until DATETIME DEFAULT NULL,
                credits INTEGER DEFAULT 50,
                referred_by INTEGER DEFAULT NULL,
                banned INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Content
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content (
                content_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                title TEXT,
                description TEXT,
                rating REAL,
                genres TEXT,
                thumbnail_url TEXT,
                master_url TEXT,
                hit_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Short Links
        await db.execute("""
            CREATE TABLE IF NOT EXISTS short_links (
                slug TEXT PRIMARY KEY,
                long_url TEXT,
                user_id INTEGER,
                clicks INTEGER DEFAULT 0,
                content_id INTEGER DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME DEFAULT NULL
            )
        """)

        # Create Token Links
        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_links (
                token TEXT PRIMARY KEY,
                content_id INTEGER,
                user_id INTEGER,
                max_uses INTEGER DEFAULT 0,
                uses INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME DEFAULT NULL
            )
        """)

        # Create Referrals
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                rewarded INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Scrape History
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scrape_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content_id INTEGER,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Channels configuration table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER UNIQUE,
                channel_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Shortener configurator
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shorteners (
                user_id INTEGER PRIMARY KEY,
                api_url TEXT,
                api_token TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create Bot settings key-values
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Seed initial settings
        await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('free_limit_videos', '2')")

        # Indices for optimal query speeds
        await db.execute("CREATE INDEX IF NOT EXISTS idx_short_links_user ON short_links(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_token_links_user ON token_links(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_scrape_history_user ON scrape_history(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_scrape_history_content ON scrape_history(content_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_user ON channels(user_id)")

        await db.commit()

    # Recovery: Populate local SQLite state from MongoDB if we are running in stateless Cloud Run container
    mdb = get_mongo_db()
    if mdb is not None:
        try:
            logger.info("Syncing tables from MongoDB Atlas collections down to SQLite on cold start...")
            tables = ["users", "content", "short_links", "token_links", "referrals", "scrape_history", "channels", "shorteners", "bot_settings"]
            async with aiosqlite.connect(db_path) as s_db:
                for table in tables:
                    col = mdb[table]
                    docs = list(col.find())
                    if docs:
                        logger.info(f"Loaded {len(docs)} records for table: '{table}'")
                        for d in docs:
                            # Strip MongoDB default ObjectID to prevent type mapping failures
                            d.pop("_id", None)
                            if table == "users":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO users (user_id, username, tier, premium_until, credits, referred_by, banned, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (d.get("user_id"), d.get("username"), d.get("tier"), d.get("premium_until"), d.get("credits"), d.get("referred_by"), d.get("banned"), d.get("created_at"))
                                )
                            elif table == "content":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO content (content_id, slug, title, description, rating, genres, thumbnail_url, master_url, hit_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (d.get("content_id"), d.get("slug"), d.get("title"), d.get("description"), d.get("rating"), d.get("genres"), d.get("thumbnail_url"), d.get("master_url"), d.get("hit_count"), d.get("created_at"))
                                )
                            elif table == "short_links":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO short_links (slug, long_url, user_id, clicks, content_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (d.get("slug"), d.get("long_url"), d.get("user_id"), d.get("clicks"), d.get("content_id"), d.get("created_at"), d.get("expires_at"))
                                )
                            elif table == "token_links":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO token_links (token, content_id, user_id, max_uses, uses, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (d.get("token"), d.get("content_id"), d.get("user_id"), d.get("max_uses"), d.get("uses"), d.get("created_at"), d.get("expires_at"))
                                )
                            elif table == "referrals":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO referrals (id, referrer_id, referred_id, rewarded, created_at) VALUES (?, ?, ?, ?, ?)",
                                    (d.get("id"), d.get("referrer_id"), d.get("referred_id"), d.get("rewarded"), d.get("created_at"))
                                )
                            elif table == "scrape_history":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO scrape_history (id, user_id, content_id, scraped_at) VALUES (?, ?, ?, ?)",
                                    (d.get("id"), d.get("user_id"), d.get("content_id"), d.get("scraped_at"))
                                )
                            elif table == "channels":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO channels (id, user_id, channel_id, channel_name, created_at) VALUES (?, ?, ?, ?, ?)",
                                    (d.get("id"), d.get("user_id"), d.get("channel_id"), d.get("channel_name"), d.get("created_at"))
                                )
                            elif table == "shorteners":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO shorteners (user_id, api_url, api_token, created_at) VALUES (?, ?, ?, ?)",
                                    (d.get("user_id"), d.get("api_url"), d.get("api_token"), d.get("created_at"))
                                )
                            elif table == "bot_settings":
                                await s_db.execute(
                                    "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
                                    (d.get("key"), d.get("value"))
                                )
                await s_db.commit()
            logger.info("Dynamically recovered and synchronised database state.")
        except Exception as e:
            logger.error(f"Failed to load from MongoDB fallback: {e}")

async def push_table_to_mongo(table_name: str):
    """Fetches SQLite table entries and synchronizes them to MongoDB Atlas."""
    mdb = get_mongo_db()
    if mdb is None:
        return
    try:
        rows = await fetch_all(f"SELECT * FROM {table_name}")
        col = mdb[table_name]

        key_map = {
            "users": "user_id",
            "content": "content_id",
            "short_links": "slug",
            "token_links": "token",
            "referrals": "id",
            "scrape_history": "id",
            "channels": "id",
            "shorteners": "user_id",
            "bot_settings": "key"
        }
        key_field = key_map.get(table_name)
        if not key_field:
            return

        # Perform high speed upserts
        for r in rows:
            doc = dict(r)
            col.replace_one({key_field: doc[key_field]}, doc, upsert=True)
            
        # Clean up Mongo items that the SQLite deleted if sizes mismatch
        db_count = len(rows)
        mongo_count = col.count_documents({})
        if mongo_count > db_count:
            # Reconstruct to keep exact sync
            col.delete_many({key_field: {"$notin": [doc[key_field] for doc in rows]}})
            
    except Exception as e:
        logger.error(f"Error executing push background sync for '{table_name}' to Atlas: {e}")

async def execute(query: str, params: tuple = ()) -> int:
    """Executes a query and returns the database rowcount affected. Triggers auto-sync."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(query, params) as cursor:
            await db.commit()
            affected = cursor.rowcount

    # Inspect tables mutated
    lower_query = query.lower()
    tables = ["users", "content", "short_links", "token_links", "referrals", "scrape_history", "channels", "shorteners", "bot_settings"]
    affected_tables = [t for t in tables if t in lower_query]

    if affected_tables and any(x in lower_query for x in ["insert", "update", "delete", "replace"]):
        for table in affected_tables:
            asyncio.create_task(push_table_to_mongo(table))

    return affected

async def fetch_one(query: str, params: tuple = ()) -> Optional[dict]:
    """Fetches a single row from the database, returned as a dict."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def fetch_all(query: str, params: tuple = ()) -> list:
    """Fetches all rows returned by a query, in a list of dicts."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
