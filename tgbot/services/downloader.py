import os
import shutil
import asyncio
import logging
import aiohttp
import pyrogram
from typing import Optional
from urllib.parse import urljoin
from tgbot.config import config

logger = logging.getLogger(__name__)

async def download_video(master_url: str, output_name: str) -> Optional[str]:
    """
    Downloads an m3u8 playlist into a local mp4/ts video file.
    Utilises ffmpeg if available (lossless and extremely fast), else falls back to segment downloader.
    """
    os.makedirs("downloads", exist_ok=True)
    cleaned_name = "".join(c for c in output_name if c.isalnum() or c in "-_").strip()
    output_path = os.path.join("downloads", f"{cleaned_name}.mp4")
    
    if shutil.which("ffmpeg"):
        logger.info(f"FFmpeg detected. Executing lossless fast HLS stream compilation: {master_url}")
        cmd = [
            "ffmpeg", "-y", "-i", master_url,
            "-c", "copy", "-bsf:a", "aac_adtstoasc",
            output_path
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0 and os.path.exists(output_path) and os.getsize(output_path) > 0:
                logger.info(f"Successfully downloaded with FFmpeg to {output_path}")
                return output_path
            else:
                stderr_text = stderr.decode(errors="ignore")
                logger.warning(f"FFmpeg execution finished with status code {process.returncode}. Stderr: {stderr_text}")
        except Exception as e:
            logger.error(f"Failed to execute FFmpeg binary process: {e}")

    # Fallback Python manual segment downloader (safeguards sandbox environments)
    logger.info("FFmpeg fallback engaged. Downloading and appending TS segments manually...")
    fallback_path = os.path.join("downloads", f"{cleaned_name}.ts")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(master_url) as r:
                if r.status != 200:
                    logger.warning(f"Master playlist failed to fetch: HTTP {r.status}")
                    return None
                playlist_content = await r.text()

            # Handle multivariant nested sub-playlists
            lines = playlist_content.splitlines()
            sub_playlist_url = None
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    sub_playlist_url = urljoin(master_url, line)
                    break

            target_playlist_url = master_url
            if sub_playlist_url:
                target_playlist_url = sub_playlist_url
                async with session.get(target_playlist_url) as r:
                    if r.status == 200:
                        playlist_content = await r.text()

            # Decode segments
            segments = []
            lines = playlist_content.splitlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    segments.append(urljoin(target_playlist_url, line))

            if not segments:
                logger.warning("Empty segments list extracted from nested playlist.")
                return None

            logger.info(f"Downloading {len(segments)} stream chunks sequentially...")
            with open(fallback_path, "wb") as out_f:
                for idx, seg_url in enumerate(segments):
                    try:
                        async with session.get(seg_url, timeout=15) as sr:
                            if sr.status == 200:
                                out_f.write(await sr.read())
                            else:
                                logger.warning(f"Failed streaming segment {idx}: {seg_url}")
                    except Exception as chunk_err:
                        logger.error(f"Segment chunk download failed at index {idx}: {chunk_err}")

            if os.path.exists(fallback_path) and os.getsize(fallback_path) > 0:
                logger.info(f"Segment compilation finished. TS video saved to '{fallback_path}'")
                return fallback_path
    except Exception as e:
        logger.error(f"Fallback downloader crashed: {e}")

    return None

async def pyrogram_send_video_up_to_2gb(
    chat_id: int,
    video_path: str,
    caption: str,
    reply_markup=None,
    thumb_path: Optional[str] = None
) -> Optional[int]:
    """
    Sends file over MTProto via Pyrogram run in memory mode.
    Allows sending files/videos up to 2GB seamlessly, bypassing standard Bot API 50MB limits.
    """
    if not config.api_id or not config.api_hash:
        logger.warning("Pyrogram skipped: API_ID or API_HASH settings not configured.")
        return None

    try:
        # Create non-persistent, clean in_memory Pyrogram Client instance
        # Uses standard Bot Token identity to log in!
        client = pyrogram.Client(
            "bot_pyrogram_client",
            api_id=int(config.api_id),
            api_hash=config.api_hash,
            bot_token=config.bot_token,
            in_memory=True
        )

        async with client:
            # Map default keyboard/buttons from python-telegram-bot to pyrogram types if needed
            # We will generate custom inline query markup or let caller pass buttons
            pyrogram_markup = None
            if reply_markup:
                # Convert python-telegram-bot InlineKeyboardMarkup/Buttons to Pyrogram style
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                rows = []
                for row in reply_markup.inline_keyboard:
                    py_row = []
                    for btn in row:
                        if btn.url:
                            py_row.append(InlineKeyboardButton(text=btn.text, url=btn.url))
                        elif btn.callback_data:
                            py_row.append(InlineKeyboardButton(text=btn.text, callback_data=btn.callback_data))
                    rows.append(py_row)
                pyrogram_markup = InlineKeyboardMarkup(rows) if rows else None

            logger.info(f"MTProto Client initiating file upload of {video_path}...")
            msg = await client.send_video(
                chat_id=chat_id,
                video=video_path,
                caption=caption,
                thumb=thumb_path,
                reply_markup=pyrogram_markup,
                supports_streaming=True
            )
            logger.info("MTProto File transmission finalized successfully!")
            return msg.id if msg else None
    except Exception as e:
        logger.error(f"MTProto sending through Pyrogram failed: {e}")
    return None
