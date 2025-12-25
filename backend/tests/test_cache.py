"""
Unit tests for caching functionality.

Tests cover prompt caching, video caching, and cache expiration.
"""

import pytest
import time
from pathlib import Path
from src.cache import (
    PromptCache,
    VideoCache,
    normalize_prompt,
    generate_cache_key
)


class TestCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_normalize_prompt(self):
        """Test prompt normalization."""
        assert normalize_prompt("  Test  ") == "test"
        assert normalize_prompt("Multiple   Spaces") == "multiple spaces"
        assert normalize_prompt("UPPERCASE") == "uppercase"
    
    def test_same_prompt_same_key(self):
        """Test that identical prompts generate same key."""
        key1 = generate_cache_key("A blue circle", "m")
        key2 = generate_cache_key("A blue circle", "m")
        assert key1 == key2
    
    def test_different_quality_different_key(self):
        """Test that different qualities generate different keys."""
        key1 = generate_cache_key("A blue circle", "m")
        key2 = generate_cache_key("A blue circle", "h")
        assert key1 != key2
    
    def test_case_insensitive(self):
        """Test that keys are case-insensitive."""
        key1 = generate_cache_key("Blue Circle", "m")
        key2 = generate_cache_key("blue circle", "m")
        assert key1 == key2


class TestPromptCache:
    """Test prompt caching."""
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = PromptCache(max_size=10, ttl_hours=1)
        result = cache.get("nonexistent prompt")
        assert result is None
    
    def test_cache_hit(self):
        """Test cache hit returns cached value."""
        cache = PromptCache(max_size=10, ttl_hours=1)
        cache.set("test prompt", "expanded prompt")
        
        result = cache.get("test prompt")
        assert result == "expanded prompt"
    
    def test_cache_expiration(self):
        """Test that expired entries return None."""
        cache = PromptCache(max_size=10, ttl_hours=0.0001)  # ~0.36 seconds
        cache.set("test prompt", "expanded prompt")
        
        time.sleep(1)  # Wait for expiration
        result = cache.get("test prompt")
        assert result is None
    
    def test_lru_eviction(self):
        """Test that oldest entries are evicted when full."""
        cache = PromptCache(max_size=2, ttl_hours=1)
        
        cache.set("prompt1", "expansion1")
        time.sleep(0.1)
        cache.set("prompt2", "expansion2")
        time.sleep(0.1)
        cache.set("prompt3", "expansion3")  # Should evict prompt1
        
        assert cache.get("prompt1") is None
        assert cache.get("prompt2") == "expansion2"
        assert cache.get("prompt3") == "expansion3"
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = PromptCache(max_size=10, ttl_hours=1)
        
        # Misses
        cache.get("miss1")
        cache.get("miss2")
        
        # Hits
        cache.set("test", "value")
        cache.get("test")
        cache.get("test")
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["size"] == 1


class TestVideoCache:
    """Test video caching."""
    
    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory."""
        return tmp_path / "cache"
    
    def test_cache_miss(self, temp_cache_dir):
        """Test video cache miss."""
        cache = VideoCache(cache_dir=temp_cache_dir, ttl_days=7)
        result = cache.get("nonexistent prompt", "m")
        assert result is None
    
    def test_cache_set_and_get(self, temp_cache_dir):
        """Test storing and retrieving video."""
        cache = VideoCache(cache_dir=temp_cache_dir, ttl_days=7)
        
        # Create a dummy video file
        video_path = temp_cache_dir / "test_video.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_text("dummy video content")
        
        # Cache it
        cache.set("test prompt", str(video_path), "m")
        
        # Retrieve it
        result = cache.get("test prompt", "m")
        assert result == str(video_path)
    
    def test_cleanup_expired(self, temp_cache_dir):
        """Test expired entry cleanup."""
        cache = VideoCache(cache_dir=temp_cache_dir, ttl_days=0.00001)  # Very short TTL
        
        # Create and cache a video
        video_path = temp_cache_dir / "test_video.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_text("dummy content")
        
        cache.set("test prompt", str(video_path), "m")
        time.sleep(1)  # Wait for expiration
        
        # Cleanup
        removed = cache.cleanup_expired()
        assert removed == 1
        
        # Should be gone
        result = cache.get("test prompt", "m")
        assert result is None
