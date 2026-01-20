"""Three-tier memory cache management system."""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import Lock
import sys
import json

from ..core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    size: int
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    tier: str = "cold"
    
    def access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
        

class CacheTier:
    """Base class for cache tiers."""
    
    def __init__(self, name: str, max_size_mb: int, ttl_seconds: int):
        self.name = name
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size = 0
        self.lock = Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            entry = self.entries.get(key)
            if entry:
                # Check TTL
                if time.time() - entry.created_at > self.ttl_seconds:
                    self._evict(key)
                    return None
                    
                entry.access()
                # Move to end (most recently used)
                self.entries.move_to_end(key)
                return entry.value
                
        return None
        
    def put(self, key: str, value: Any, size: int) -> bool:
        """Put value in cache."""
        with self.lock:
            # Remove existing entry if present
            if key in self.entries:
                self._evict(key)
                
            # Check if we need to make space
            while self.current_size + size > self.max_size_bytes and self.entries:
                # Evict least recently used
                self._evict(next(iter(self.entries)))
                
            # Add new entry
            entry = CacheEntry(key=key, value=value, size=size, tier=self.name)
            self.entries[key] = entry
            self.current_size += size
            
            return True
            
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self.lock:
            return self._evict(key)
            
    def _evict(self, key: str) -> bool:
        """Evict an entry from cache."""
        if key in self.entries:
            entry = self.entries.pop(key)
            self.current_size -= entry.size
            return True
        return False
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                'name': self.name,
                'entries': len(self.entries),
                'size_mb': self.current_size / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'utilization': self.current_size / self.max_size_bytes if self.max_size_bytes > 0 else 0
            }


class ThreeTierMemoryCache:
    """Three-tier memory cache system with hot, warm, and cold tiers."""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize tiers
        total_cache_mb = config.cache.max_size_mb
        
        # Allocate cache space: Hot (20%), Warm (30%), Cold (50%)
        self.hot_cache = CacheTier(
            "hot",
            int(total_cache_mb * 0.2),
            config.cache.hot_cache_ttl
        )
        
        self.warm_cache = CacheTier(
            "warm",
            int(total_cache_mb * 0.3),
            config.cache.warm_cache_ttl
        )
        
        # Cold storage is handled by the database/vector store
        # We keep a reference cache for frequently accessed cold items
        self.cold_cache = CacheTier(
            "cold",
            int(total_cache_mb * 0.5),
            config.cache.warm_cache_ttl * 2
        )
        
        # Promotion thresholds
        self.warm_to_hot_threshold = 5  # Access count
        self.cold_to_warm_threshold = 3  # Access count
        
        # Track overall statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'promotions': 0,
            'evictions': 0
        }
        
    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """Get value from cache, returns (value, tier)."""
        # Check hot cache first
        value = self.hot_cache.get(key)
        if value is not None:
            self.stats['hits'] += 1
            return value, "hot"
            
        # Check warm cache
        value = self.warm_cache.get(key)
        if value is not None:
            self.stats['hits'] += 1
            # Check for promotion
            entry = self.warm_cache.entries.get(key)
            if entry and entry.access_count >= self.warm_to_hot_threshold:
                self._promote(key, "warm", "hot")
            return value, "warm"
            
        # Check cold cache
        value = self.cold_cache.get(key)
        if value is not None:
            self.stats['hits'] += 1
            # Check for promotion
            entry = self.cold_cache.entries.get(key)
            if entry and entry.access_count >= self.cold_to_warm_threshold:
                self._promote(key, "cold", "warm")
            return value, "cold"
            
        self.stats['misses'] += 1
        return None, None
        
    def put(self, key: str, value: Any, tier: str = "cold") -> bool:
        """Put value in specified tier."""
        # Calculate size
        size = self._calculate_size(value)
        
        if tier == "hot":
            return self.hot_cache.put(key, value, size)
        elif tier == "warm":
            return self.warm_cache.put(key, value, size)
        else:
            return self.cold_cache.put(key, value, size)
            
    def _promote(self, key: str, from_tier: str, to_tier: str):
        """Promote entry from one tier to another."""
        # Get source and destination tiers
        tiers = {
            "hot": self.hot_cache,
            "warm": self.warm_cache,
            "cold": self.cold_cache
        }
        
        source = tiers.get(from_tier)
        dest = tiers.get(to_tier)
        
        if not source or not dest:
            return
            
        # Get entry from source
        with source.lock:
            entry = source.entries.get(key)
            if not entry:
                return
                
            # Remove from source
            source._evict(key)
            
        # Add to destination
        dest.put(key, entry.value, entry.size)
        
        self.stats['promotions'] += 1
        logger.debug(f"Promoted {key} from {from_tier} to {to_tier}")
        
    def _calculate_size(self, value: Any) -> int:
        """Estimate size of a value in bytes."""
        if isinstance(value, str):
            return len(value.encode('utf-8'))
        elif isinstance(value, (list, dict)):
            # Serialize to estimate size
            try:
                return len(json.dumps(value).encode('utf-8'))
            except:
                return sys.getsizeof(value)
        else:
            return sys.getsizeof(value)
            
    def invalidate(self, key: str):
        """Invalidate entry across all tiers."""
        self.hot_cache.remove(key)
        self.warm_cache.remove(key)
        self.cold_cache.remove(key)
        
    def invalidate_pattern(self, pattern: str):
        """Invalidate all entries matching pattern."""
        import fnmatch
        
        for tier in [self.hot_cache, self.warm_cache, self.cold_cache]:
            with tier.lock:
                keys_to_remove = [
                    k for k in tier.entries.keys()
                    if fnmatch.fnmatch(k, pattern)
                ]
                for key in keys_to_remove:
                    tier._evict(key)
                    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            'overall': self.stats,
            'tiers': {
                'hot': self.hot_cache.get_stats(),
                'warm': self.warm_cache.get_stats(),
                'cold': self.cold_cache.get_stats()
            },
            'hit_rate': self.stats['hits'] / (self.stats['hits'] + self.stats['misses'])
            if (self.stats['hits'] + self.stats['misses']) > 0 else 0
        }
        
    def clear(self):
        """Clear all caches."""
        for tier in [self.hot_cache, self.warm_cache, self.cold_cache]:
            with tier.lock:
                tier.entries.clear()
                tier.current_size = 0
                
        self.stats = {
            'hits': 0,
            'misses': 0,
            'promotions': 0,
            'evictions': 0
        }