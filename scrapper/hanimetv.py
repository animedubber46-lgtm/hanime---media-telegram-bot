from __future__ import annotations
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse, quote_plus
from curl_cffi import requests as cf
import aiohttp
from scrapper import ScrapResult, ScrapError, register
from scrapper.browser import new_context
import secret

logger = logging.getLogger(__name__)

SITE_KEY = "hanimetv"
KEYWORDS = ["hanime.tv"]

_REFERER = "https://hanime.tv/"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Referer": _REFERER,
    "Accept": "*/*",
}

_CDN_HOSTS = [
    "highwinds-cdn.com",
    "m3u8s.highwinds-cdn.com",
    "hanime-videos.com",
    "hanime1.me",
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def _slug_from_url(url: str) -> Optional[str]:
    m = re.search(r"/videos/hentai/([^/?#]+)", url)
    return m.group(1) if m else None


def _is_cdn_stream(url: str) -> bool:
    """Detect the exact m3u8 master we want."""
    lo = url.lower()
    host = urlparse(url).netloc.lower()
    return (
        any(cdn in host for cdn in _CDN_HOSTS)
        and ".m3u8" in lo
    )


def _fetch_text_sync(url: str) -> str:
    r = cf.get(url, headers=_HEADERS, impersonate="chrome", timeout=20)
    r.raise_for_status()
    return r.text


# ── Jikan API Thumbnail (only thumbnail method now) ───────────────────────────
async def _fetch_jikan_thumbnail(title: str) -> Optional[str]:
    if not title:
        return None
    query = quote_plus(title)
    api_url = f"https://api.jikan.moe/v4/anime?q={query}"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(api_url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                results = data.get("data", [])
                if results:
                    large_url = (
                        results[0]
                        .get("images", {})
                        .get("jpg", {})
                        .get("large_image_url")
                    )
                    if large_url:
                        logger.info("[hanimetv] Jikan thumbnail fetched: %s", large_url[:80])
                        return large_url
    except Exception as e:
        logger.debug("[hanimetv] Jikan API failed: %s", e)
    logger.warning("[hanimetv] no Jikan thumbnail found for: %s", title)
    return None


# ── Browser resolver (EXACTLY your original code - no thumbnail stuff) ───────
async def _resolve_via_browser(url: str) -> tuple[str, str]:
    """Fast direct interception of the m3u8 master."""
    master_url: Optional[str] = None
    _found = asyncio.Event()

    async with new_context(extra_http_headers={"Referer": _REFERER}) as ctx:
        page = await ctx.new_page()

        async def _on_request(req):
            nonlocal master_url
            if _is_cdn_stream(req.url) and master_url is None:
                master_url = req.url
                _found.set()
                logger.info("[hanimetv] intercepted master m3u8 → %s", req.url)

        async def _on_response(resp):
            nonlocal master_url
            if _is_cdn_stream(resp.url) and master_url is None:
                master_url = resp.url
                _found.set()
                logger.info("[hanimetv] intercepted master m3u8 → %s", resp.url)

        page.on("request", _on_request)
        page.on("response", _on_response)

        logger.info("[hanimetv] navigating → %s", url)
        try:
            await page.goto(
                url, wait_until="commit",          # ← minor speed tweak (faster than domcontentloaded)
                timeout=secret.PLAYWRIGHT_TIMEOUT
            )
        except Exception as e:
            logger.warning("[hanimetv] goto: %s", e)

        # ── Title (exactly like before) ─────────────────────────────────────
        title = ""
        try:
            # og:title
            og_t = await page.query_selector('meta[property="og:title"]')
            if og_t:
                title = (await og_t.get_attribute("content") or "").strip()
        except Exception:
            pass

        # Force player start (exactly your original)
        for sel in [
            "button[aria-label='Play Video']",
            ".vjs-big-play-button",
            "button.play",
            ".play-button",
            "svg[aria-label='Play']",
            "[class*='play']",
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True, timeout=800)   # ← minor: 2000→800
                    break
            except Exception:
                pass

        try:
            await page.mouse.click(640, 400)
            await page.evaluate(
                "()=>{const v=document.querySelector('video');"
                "if(v){v.muted=true;v.play().catch(()=>{})}}"
            )
        except Exception:
            pass

        # Wait for the m3u8 master
        try:
            await asyncio.wait_for(_found.wait(), timeout=25)
        except asyncio.TimeoutError:
            raise ScrapError(
                f"[{SITE_KEY}] Timed out waiting for m3u8 master. "
                "Page structure may have changed."
            )

    if not master_url:
        raise ScrapError(f"[{SITE_KEY}] No m3u8 master intercepted.")

    return master_url, title


# ── Main resolver ─────────────────────────────────────────────────────────────
async def resolve(url: str) -> ScrapResult:
    slug = _slug_from_url(url)
    if not slug:
        raise ScrapError(
            f"[{SITE_KEY}] Unrecognised URL — expected "
            f"https://hanime.tv/videos/hentai/<slug>, got: {url}"
        )

    logger.info("[hanimetv] resolving → %s", url)

    # ←←← MINOR SPEED BOOST: start Jikan in parallel (runs while browser loads)
    search_title_from_slug = slug.replace("-", " ").title()
    thumbnail_task = asyncio.create_task(_fetch_jikan_thumbnail(search_title_from_slug))

    master_url, title = await _resolve_via_browser(url)

    logger.info("[hanimetv] intercepted master → %s", master_url[:100])

    search_title = title or search_title_from_slug

    # ←←← wait for thumbnail (already running in background)
    thumbnail = await thumbnail_task

    # ONLY "best (auto)" — no quality parsing
    qualities = [{
        "label": "best (auto)",
        "url": master_url,
        "master_url": master_url,
        "height": 0,
        "bandwidth": 0,
        "ytdlp_format": "best",
    }]

    logger.info(
        "[hanimetv] resolved '%s' thumb=%s qualities=['best (auto)']",
        search_title, bool(thumbnail),
    )

    return ScrapResult(
        url=master_url,
        title=search_title,
        qualities=qualities,
        thumbnail=thumbnail,
        extra={"headers": _HEADERS, "referer": _REFERER},
    )


# ── Self-register ─────────────────────────────────────────────────────────────
register(SITE_KEY, KEYWORDS, resolve)
