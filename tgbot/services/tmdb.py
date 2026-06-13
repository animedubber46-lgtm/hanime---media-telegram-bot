import aiohttp
import logging
from typing import Optional, Dict, Any
from tgbot.config import config

logger = logging.getLogger(__name__)

async def get_metadata(title: str, slug: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Searches TMDB for matching anime/multi-media entry to complement metadata.
    
    Returns:
        Dict with {description, rating, genres, tmdb_id, poster_url} or None on empty/error.
    """
    api_key = config.tmdb_api_key
    if not api_key or api_key == "MY_TMDB_API_KEY" or api_key == "your_tmdb_api_key_here":
        logger.info("TMDB query skipped: TMDB_API_KEY is not configured.")
        return None

    # Clean the title to strip episode numbers, season tags, and uncensored marks to maximize TMDB match rates
    import re
    cleaned_title = re.sub(r'(?i)\b(episode|ep)?\.?\s*\d+\b', '', title)
    cleaned_title = re.sub(r'(?i)\b(ova|uncensored|subbed|dubbed|complete|full)\b', '', cleaned_title)
    cleaned_title = re.sub(r'[-\s（）\(\)]+$', '', cleaned_title)
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    if not cleaned_title:
        cleaned_title = title
        
    # Generate sequential query variations for maximum matching
    queries_to_try = [cleaned_title]

    if title and title != cleaned_title and title not in queries_to_try:
        queries_to_try.append(title)

    if slug:
        slug_cleaned = re.sub(r'-\d+$', '', slug)
        slug_cleaned = re.sub(r'(?i)-ep(isode)?-\d+$', '', slug_cleaned)
        if slug_cleaned and slug_cleaned not in queries_to_try:
            queries_to_try.append(slug_cleaned)
        
        slug_with_spaces = slug_cleaned.replace('-', ' ')
        if slug_with_spaces and slug_with_spaces not in queries_to_try:
            queries_to_try.append(slug_with_spaces)

    hyphenated = cleaned_title.replace(' ', '-')
    if hyphenated and hyphenated not in queries_to_try:
        queries_to_try.append(hyphenated)

    words = cleaned_title.split()
    if len(words) > 2:
        first_two = " ".join(words[:2])
        if first_two and first_two not in queries_to_try:
            queries_to_try.append(first_two)

    url = "https://api.themoviedb.org/3/search/multi"
    
    for query in queries_to_try:
        logger.info(f"Searching TMDB for: '{query}' (original: '{title}', slug: '{slug}')")
        params = {
            "api_key": api_key,
            "query": query,
            "language": "en",
            "page": 1,
            "include_adult": "true"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status != 200:
                        logger.warning(f"TMDB query returned HTTP {response.status}")
                        continue
                        
                    data = await response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        continue
                        
                    # Take the top match
                    top_match = results[0]
                    
                    # Fetch details
                    overview = top_match.get("overview") or top_match.get("description", "")
                    rating = float(top_match.get("vote_average", 0.0))
                    
                    # TMDB returns posters relative to base paths
                    poster_path = top_match.get("poster_path") or top_match.get("backdrop_path")
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                    
                    tmdb_id = top_match.get("id")
                    media_type = top_match.get("media_type", "movie")
                    
                    # Get beautiful genre names
                    genre_ids = top_match.get("genre_ids", [])
                    genre_map = {
                        16: "Animation",
                        35: "Comedy",
                        18: "Drama",
                        10749: "Romance",
                        14: "Fantasy",
                        9648: "Mystery"
                    }
                    genres = [genre_map[g] for g in genre_ids if g in genre_map]
                    genre_str = ", ".join(genres) if genres else "Anime"
                    
                    logger.info(f"Successfully matched TMDB entry for query: '{query}'")
                    return {
                        "description": overview,
                        "rating": rating if rating > 0.1 else None,
                        "genres": genre_str,
                        "tmdb_id": tmdb_id,
                        "poster_url": poster_url,
                        "media_type": media_type
                    }
        except Exception as e:
            logger.warning(f"Error checking variation query '{query}' from TMDB: {e}")
            continue

    return None
