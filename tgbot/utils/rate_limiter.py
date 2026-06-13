import time
from cachetools import TTLCache
from typing import Dict, List

class RateLimiter:
    def __init__(self):
        # We store list of request timestamps per user_id as cache values.
        # Max 10,000 distinct user/action caches per action bucket.
        self._caches: Dict[str, TTLCache] = {}

    def get_user_timestamps(self, user_id: int, action: str, window: int) -> List[float]:
        """Gets and cleans old timestamps for a specific user action."""
        # Ensure we have a cache bucket for this action.
        # The TTL is set to the rate limit window itself so inactive players clear up completely.
        if action not in self._caches:
            self._caches[action] = TTLCache(maxsize=10000, ttl=window)
        
        cache = self._caches[action]
        now = time.time()
        
        # Pull request timestamps
        timestamps = cache.get(user_id, [])
        # Filter out timestamps outside our current rolling time block
        valid_timestamps = [t for t in timestamps if now - t < window]
        
        return valid_timestamps

    def check(self, user_id: int, action: str, limit: int, window: int) -> bool:
        """
        Validates whether the user's operation fits within rolling limits.
        
        Returns:
            True if allowed (limit not reached).
            False if rate limited (limit exceeded).
        """
        timestamps = self.get_user_timestamps(user_id, action, window)
        
        if len(timestamps) >= limit:
            return False
            
        # Append latest action time and restore
        timestamps.append(time.time())
        self._caches[action][user_id] = timestamps
        return True

    def remaining(self, user_id: int, action: str, limit: int, window: int) -> int:
        """Returns the number of remaining queries in the current rolling window."""
        timestamps = self.get_user_timestamps(user_id, action, window)
        return max(0, limit - len(timestamps))

    def time_to_wait(self, user_id: int, action: str, limit: int, window: int) -> float:
        """If rate limited, calculates the remaining seconds before the next query is allowed."""
        timestamps = self.get_user_timestamps(user_id, action, window)
        if len(timestamps) < limit:
            return 0.0
        # The earliest timestamp in our window needs to slide out
        oldest_ts = min(timestamps)
        now = time.time()
        elapsed = now - oldest_ts
        return max(0.1, float(window - elapsed))

# Global rate limiter instance
rate_limiter = RateLimiter()
