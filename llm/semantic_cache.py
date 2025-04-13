import logging
import json
import time
import asyncio
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import SemanticCacheEntry

logger = logging.getLogger(__name__)

class SemanticCache:
    """Semantic cache for LLM queries using embeddings for similarity matching"""
    
    def __init__(self):
        self.similarity_threshold = settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD
        self.cache_expiry_seconds = settings.SEMANTIC_CACHE_EXPIRY_SECONDS
        self.initialized = False
        
    async def initialize(self):
        """Initialize the semantic cache"""
        if self.initialized:
            return
            
        logger.info("Initializing Semantic Cache")
        
        # Start background task for cache cleanup
        asyncio.create_task(self.cleanup_loop())
        
        self.initialized = True
        logger.info("Semantic Cache initialized")
        
    async def cleanup_loop(self):
        """Background task to periodically clean up expired cache entries"""
        while True:
            try:
                await self._clean_expired_entries()
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {str(e)}")
                await asyncio.sleep(300)  # Shorter wait on error
                
    async def _clean_expired_entries(self):
        """Remove expired entries from the cache"""
        logger.debug("Cleaning up expired semantic cache entries")
        
        async with get_db() as db:
            from sqlalchemy import delete
            
            # Delete expired entries
            now = datetime.utcnow()
            stmt = delete(SemanticCacheEntry).where(SemanticCacheEntry.expires_at < now)
            result = await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Removed {result.rowcount} expired semantic cache entries")
            
    async def compute_embedding(self, text: str) -> List[float]:
        """
        Compute embedding for a text string
        
        Note: In a production environment, this would use a dedicated embedding model.
        For this implementation, we use a simplified approach.
        """
        # This is a simplified embedding function - in production you'd use a proper embedding model
        # like Sentence Transformers, OpenAI embeddings API, or similar
        
        # Create a simple hash-based embedding
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert hash to a list of floats
        embedding = []
        for i in range(0, len(hash_bytes), 2):
            if i+1 < len(hash_bytes):
                val = (hash_bytes[i] * 256 + hash_bytes[i+1]) / 65535.0
                embedding.append(val)
                
        # Pad or truncate to fixed length (16 dimensions for this example)
        embedding = embedding[:16]
        while len(embedding) < 16:
            embedding.append(0.0)
            
        return embedding
        
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
        
    async def get(self, prompt: str, model_id: int, cache_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a prompt
        
        Returns None if no suitable cache entry found
        """
        if not settings.ENABLE_SEMANTIC_CACHE:
            return None
            
        # Try direct cache key lookup first (faster)
        if cache_key:
            async with get_db() as db:
                from sqlalchemy import select
                
                # Look for exact match by cache key
                stmt = select(SemanticCacheEntry).where(
                    SemanticCacheEntry.cache_key == cache_key,
                    SemanticCacheEntry.model_id == model_id,
                    SemanticCacheEntry.expires_at > datetime.utcnow()
                )
                
                result = await db.execute(stmt)
                entry = result.scalars().first()
                
                if entry:
                    # Update hit count
                    entry.hit_count += 1
                    await db.commit()
                    
                    return {
                        "response": entry.response_text,
                        "prompt_tokens": 0,  # We don't store these in the DB
                        "completion_tokens": 0,
                        "model_id": entry.model_id
                    }
                    
        # Compute embedding for prompt
        prompt_embedding = await self.compute_embedding(prompt)
        
        # Search for similar entries
        async with get_db() as db:
            from sqlalchemy import select
            
            # Get all non-expired entries for this model
            stmt = select(SemanticCacheEntry).where(
                SemanticCacheEntry.model_id == model_id,
                SemanticCacheEntry.expires_at > datetime.utcnow()
            )
            
            result = await db.execute(stmt)
            entries = result.scalars().all()
            
            for entry in entries:
                if not entry.query_embedding:
                    continue
                    
                # Parse stored embedding
                try:
                    entry_embedding = json.loads(entry.query_embedding)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse embedding for cache entry {entry.id}")
                    continue
                    
                # Compute similarity
                similarity = self.cosine_similarity(prompt_embedding, entry_embedding)
                
                if similarity >= self.similarity_threshold:
                    # Update hit count
                    entry.hit_count += 1
                    
                    # Store cache key if provided
                    if cache_key and not entry.cache_key:
                        entry.cache_key = cache_key
                        
                    await db.commit()
                    
                    logger.debug(f"Semantic cache hit (similarity: {similarity:.4f})")
                    
                    return {
                        "response": entry.response_text,
                        "prompt_tokens": 0,  # We don't store these in the DB
                        "completion_tokens": 0,
                        "model_id": entry.model_id
                    }
                    
        # No suitable cache entry found
        return None
        
    async def add(
        self,
        prompt: str,
        response: str,
        model_id: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cache_key: Optional[str] = None
    ) -> None:
        """Add a new entry to the semantic cache"""
        if not settings.ENABLE_SEMANTIC_CACHE:
            return
            
        # Compute embedding for prompt
        prompt_embedding = await self.compute_embedding(prompt)
        
        # Store as JSON string
        embedding_json = json.dumps(prompt_embedding)
        
        # Create cache entry
        cache_entry = SemanticCacheEntry(
            query_text=prompt,
            query_embedding=embedding_json,
            response_text=response,
            model_id=model_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.cache_expiry_seconds),
            hit_count=0,
            cache_key=cache_key
        )
        
        # Store in database
        async with get_db() as db:
            db.add(cache_entry)
            await db.commit()
            
        logger.debug(f"Added entry to semantic cache with key {cache_key}")
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with get_db() as db:
            from sqlalchemy import select, func
            
            # Get total entries
            stmt = select(func.count()).select_from(SemanticCacheEntry)
            result = await db.execute(stmt)
            total_entries = result.scalar()
            
            # Get active entries (not expired)
            stmt = select(func.count()).select_from(SemanticCacheEntry).where(
                SemanticCacheEntry.expires_at > datetime.utcnow()
            )
            result = await db.execute(stmt)
            active_entries = result.scalar()
            
            # Get total hits
            stmt = select(func.sum(SemanticCacheEntry.hit_count)).select_from(SemanticCacheEntry)
            result = await db.execute(stmt)
            total_hits = result.scalar() or 0
            
            # Get entries by model
            stmt = select(
                SemanticCacheEntry.model_id,
                func.count()
            ).group_by(SemanticCacheEntry.model_id)
            result = await db.execute(stmt)
            entries_by_model = {str(model_id): count for model_id, count in result.all()}
            
            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": total_entries - active_entries,
                "total_hits": total_hits,
                "entries_by_model": entries_by_model,
                "similarity_threshold": self.similarity_threshold,
                "cache_expiry_seconds": self.cache_expiry_seconds
            }
