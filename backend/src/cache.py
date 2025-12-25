"""
Caching layer for Prompt2Frame to improve performance and reduce costs.

Implements two-tier caching:
1. In-memory LRU cache for prompt expansions (fast, temporary)
2. File-system cache tracking for generated videos (persistent)
"""

import hashlib
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def normalize_prompt(prompt: str) -> str:
    """
    Normalize prompt for consistent cache keys.
    
    Args:
        prompt: Raw user prompt
        
    Returns:
        Normalized prompt (lowercase, stripped, single spaces)
    """
    # Convert to lowercase
    normalized = prompt.lower().strip()
    
    # Replace multiple spaces with single space
    normalized = ' '.join(normalized.split())
    
    return normalized


def generate_cache_key(prompt: str, quality: str = 'm') -> str:
    """
    Generate cache key from prompt and quality.
    
    Args:
        prompt: User prompt
        quality: Video quality ('l', 'm', 'h')
        
    Returns:
        Cache key (hex digest)
    """
    normalized = normalize_prompt(prompt)
    key_string = f"{normalized}:{quality}"
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]


class PromptCache:
    """
    In-memory LRU cache for prompt expansions.
    
    Uses functools.lru_cache under the hood with TTL support.
    """
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        """
        Initialize prompt cache.
        
        Args:
            max_size: Maximum number of cached prompts
            ttl_hours: Time-to-live in hours
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self._cache: Dict[str, tuple[str, float]] = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, prompt: str) -> Optional[str]:
        """
        Get cached prompt expansion.
        
        Args:
            prompt: Original prompt
            
        Returns:
            Expanded prompt if cached and not expired, None otherwise
        """
        cache_key = generate_cache_key(prompt)
        
        if cache_key in self._cache:
            expanded_prompt, timestamp = self._cache[cache_key]
            
            # Check if expired
            if time.time() - timestamp < self.ttl_seconds:
                self._hits += 1
                logger.debug(f"Prompt cache HIT for key: {cache_key}")
                return expanded_prompt
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
                logger.debug(f"Prompt cache EXPIRED for key: {cache_key}")
        
        self._misses += 1
        logger.debug(f"Prompt cache MISS for key: {cache_key}")
        return None
    
    def set(self, prompt: str, expanded_prompt: str):
        """
        Cache a prompt expansion.
        
        Args:
            prompt: Original prompt
            expanded_prompt: Expanded version
        """
        cache_key = generate_cache_key(prompt)
        
        # Implement LRU by removing oldest if at capacity
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            logger.debug(f"Evicted oldest cache entry: {oldest_key}")
        
        self._cache[cache_key] = (expanded_prompt, time.time())
        logger.debug(f"Prompt cached with key: {cache_key}")
    
    def clear(self):
        """Clear all cached prompts."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Prompt cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }


class VideoCache:
    """
    File-system based cache for generated videos.
    
    Tracks which videos exist and when they were created.
    """
    
    def __init__(self, cache_dir: Path, ttl_days: int = 7):
        """
        Initialize video cache.
        
        Args:
            cache_dir: Directory containing cached videos
            ttl_days: Time-to-live in days
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_days * 24 * 3600
        self._metadata_file = self.cache_dir / "cache_metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load cache metadata from disk."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    self._metadata = json.load(f)
                logger.debug(f"Loaded cache metadata: {len(self._metadata)} entries")
            except Exception as e:
                logger.error(f"Failed to load cache metadata: {e}")
                self._metadata = {}
    
    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self._metadata_file, 'w') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def get(self, prompt: str, quality: str = 'm') -> Optional[str]:
        """
        Get cached video URL.
        
        Args:
            prompt: Original prompt
            quality: Video quality
            
        Returns:
            Video path if cached and not expired, None otherwise
        """
        cache_key = generate_cache_key(prompt, quality)
        
        if cache_key in self._metadata:
            entry = self._metadata[cache_key]
            video_path = Path(entry['video_path'])
            created_at = entry['created_at']
            
            # Check if expired
            age = time.time() - created_at
            if age < self.ttl_seconds and video_path.exists():
                logger.info(f"Video cache HIT: {cache_key} (age: {age/3600:.1f}h)")
                return str(video_path)
            else:
                # Expired or missing, remove from metadata
                del self._metadata[cache_key]
                self._save_metadata()
                logger.debug(f"Video cache entry removed (expired or missing): {cache_key}")
        
        logger.debug(f"Video cache MISS: {cache_key}")
        return None
    
    def set(self, prompt: str, video_path: str, quality: str = 'm'):
        """
        Register a generated video in cache.
        
        Args:
            prompt: Original prompt
            video_path: Path to generated video
            quality: Video quality
        """
        cache_key = generate_cache_key(prompt, quality)
        
        self._metadata[cache_key] = {
            'prompt': normalize_prompt(prompt),
            'video_path': video_path,
            'quality': quality,
            'created_at': time.time()
        }
        
        self._save_metadata()
        logger.info(f"Video cached: {cache_key}")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from metadata.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._metadata.items():
            age = current_time - entry['created_at']
            video_path = Path(entry['video_path'])
            
            if age >= self.ttl_seconds or not video_path.exists():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._metadata[key]
        
        if expired_keys:
            self._save_metadata()
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = 0
        for entry in self._metadata.values():
            video_path = Path(entry['video_path'])
            if video_path.exists():
                total_size += video_path.stat().st_size
        
        return {
            "entries": len(self._metadata),
            "total_size_mb": total_size / (1024 * 1024),
            "ttl_days": self.ttl_seconds / (24 * 3600)
        }


# Global cache instances
prompt_cache = PromptCache(max_size=100, ttl_hours=24)
video_cache: Optional[VideoCache] = None  # Initialized in app.py


def initialize_video_cache(media_root: Path):
    """Initialize the video cache with media directory."""
    global video_cache
    video_cache = VideoCache(cache_dir=media_root, ttl_days=7)
    logger.info(f"Video cache initialized: {media_root}")
