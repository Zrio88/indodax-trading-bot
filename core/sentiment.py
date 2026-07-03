"""
Fear & Greed Index from alternative.me
Caches results for 1 hour to avoid rate limiting
"""
from datetime import datetime, timedelta
import json
import os
import urllib.request
import urllib.error


class Sentiment:
    """
    Fetch and cache Fear & Greed Index from alternative.me
    
    The index ranges from 0 (Extreme Fear) to 100 (Extreme Greed):
    - 0-20: Extreme Fear
    - 21-40: Fear
    - 41-60: Neutral
    - 61-80: Greed
    - 81-100: Extreme Greed
    
    Higher fear values generally indicate better buying opportunities.
    """
    
    API_URL = "https://api.alternative.me/fng/"
    CACHE_FILE = "storage/sentiment_cache.json"
    CACHE_TTL = 3600  # 1 hour cache
    
    def __init__(self):
        """Initialize sentiment with cached data"""
        self.cache = self._load_cache()
        self.value = self.cache.get("value", 50)
        self.classification = self.cache.get("classification", "Neutral")
        self.last_fetch = datetime.fromisoformat(self.cache.get("timestamp", "1970-01-01"))
    
    def _load_cache(self) -> dict:
        """Load cached sentiment data from file"""
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self, data: dict):
        """Save sentiment data to cache file"""
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
        with open(self.CACHE_FILE, "w") as f:
            json.dump(data, f)
    
    def _classify(self, score: int) -> str:
        """Classify fear & greed score into categories"""
        if score <= 10:
            return "Extreme Fear"
        elif score <= 30:
            return "Fear"
        elif score <= 70:
            return "Neutral"
        elif score <= 90:
            return "Greed"
        else:
            return "Extreme Greed"
    
    def _fetch_from_api(self) -> dict:
        """Fetch latest sentiment from API (sync)"""
        try:
            with urllib.request.urlopen(self.API_URL, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if data.get("data") and len(data["data"]) > 0:
                        return {
                            "value": int(data["data"][0]["value"]),
                            "classification": self._classify(int(data["data"][0]["value"])),
                            "timestamp": datetime.utcnow().isoformat()
                        }
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
            print(f"Error fetching sentiment: {e}")
        return None
    
    def score(self) -> float:
        """
        Get current sentiment score normalized to 0-1 range
        
        Returns:
            float: 0.0 (Extreme Fear) to 1.0 (Extreme Greed)
        """
        # Refresh cache if expired
        if datetime.utcnow() - self.last_fetch > timedelta(seconds=self.CACHE_TTL):
            self._update_cache()
        return self.value / 100.0
    
    def classification(self) -> str:
        """
        Get current sentiment classification
        
        Returns:
            str: One of "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
        """
        if datetime.utcnow() - self.last_fetch > timedelta(seconds=self.CACHE_TTL):
            self._update_cache()
        return self.classification
    
    def _update_cache(self):
        """Update cache from API (sync)"""
        data = self._fetch_from_api()
        if data:
            self.cache = data
            self.value = data["value"]
            self.classification = data["classification"]
            self.last_fetch = datetime.fromisoformat(data["timestamp"])
            self._save_cache(data)
    
    def get_raw_value(self) -> int:
        """Get raw sentiment value (0-100)"""
        return self.value
