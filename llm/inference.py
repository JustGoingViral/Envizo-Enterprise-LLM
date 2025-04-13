import os
import json
import logging
import time
import httpx
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_async_db_ctx
from models import Query, QueryStatus, LLMModel
from utils import log_query, update_query_response, compute_cache_key
from .load_balancer import LLMLoadBalancer
from .semantic_cache import SemanticCache

logger = logging.getLogger(__name__)

class LLMInferenceManager:
    """Manager for LLM inference across multiple servers"""

    def __init__(self):
        self.load_balancer = LLMLoadBalancer()
        self.semantic_cache = SemanticCache() if settings.ENABLE_SEMANTIC_CACHE else None

    async def initialize(self):
        """Initialize the inference manager"""
        logger.info("Initializing LLM Inference Manager")
        await self.load_balancer.initialize()
        if self.semantic_cache:
            await self.semantic_cache.initialize()

    async def generate(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        source: str = "web_ui",
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Generate text using the LLM"""
        start_time = time.time()

        # Use provided db session or create a new one
        if db is None:
            async with get_async_db_ctx() as db:
                return await self._generate_with_db(
                    db=db,
                    prompt=prompt,
                    model_name=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    stop=stop,
                    user_id=user_id,
                    source=source,
                    client_ip=client_ip,
                    metadata=metadata,
                    start_time=start_time
                )
        else:
            return await self._generate_with_db(
                db=db,
                prompt=prompt,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop,
                user_id=user_id,
                source=source,
                client_ip=client_ip,
                metadata=metadata,
                start_time=start_time
            )

    async def _generate_with_db(
        self,
        db: AsyncSession,
        prompt: str,
        model_name: Optional[str],
        max_tokens: int,
        temperature: float,
        top_p: float,
        frequency_penalty: float,
        presence_penalty: float,
        stop: Optional[List[str]],
        user_id: Optional[int],
        source: str,
        client_ip: Optional[str],
        metadata: Optional[Dict[str, Any]],
        start_time: float
    ) -> Dict[str, Any]:
        """Internal method to generate text with a db session"""
        # Determine model to use
        from sqlalchemy import select
        model_name = model_name or settings.LLM_DEFAULT_MODEL

        # Get model from database
        result = await db.execute(
            select(LLMModel).where(LLMModel.name == model_name)
        )
        model = result.scalars().first()

        if not model:
            logger.warning(f"Model {model_name} not found, using default")
            result = await db.execute(
                select(LLMModel).where(LLMModel.name == settings.LLM_DEFAULT_MODEL)
            )
            model = result.scalars().first()

            if not model:
                logger.error("Default model not found in database")
                return {
                    "error": "Model not found",
                    "success": False
                }

        # Log the query
        query_id = await log_query(
            db=db,
            user_id=user_id,
            model_id=model.id,
            query_text=prompt,
            source=source,
            client_ip=client_ip,
            metadata=metadata
        )

        # Check semantic cache if enabled
        cached_response = None
        cache_key = None

        if self.semantic_cache and settings.ENABLE_SEMANTIC_CACHE:
            cache_key = compute_cache_key(prompt, model.name)
            cached_response = await self.semantic_cache.get(prompt, model.id, cache_key)

        if cached_response:
            # Use cached response
            processing_time = (time.time() - start_time) * 1000  # ms

            # Update query with cached response
            await update_query_response(
                db=db,
                query_id=query_id,
                response_text=cached_response["response"],
                token_count_prompt=cached_response["prompt_tokens"],
                token_count_response=cached_response["completion_tokens"],
                processing_time_ms=processing_time,
                status="completed",
                cached=True,
                cache_key=cache_key
            )

            return {
                "response": cached_response["response"],
                "model": model.name,
                "prompt_tokens": cached_response["prompt_tokens"],
                "completion_tokens": cached_response["completion_tokens"],
                "total_tokens": cached_response["prompt_tokens"] + cached_response["completion_tokens"],
                "processing_time_ms": processing_time,
                "query_id": query_id,
                "cached": True,
                "success": True
            }

        # Get server for inference
        server = await self.load_balancer.get_server(model.name)

        if not server:
            logger.error(f"No suitable server found for model {model.name}")

            # Update query with error
            await update_query_response(
                db=db,
                query_id=query_id,
                response_text="",
                token_count_prompt=0,
                token_count_response=0,
                processing_time_ms=0,
                status="failed",
                error_message="No suitable server available"
            )

            return {
                "error": "No suitable server available",
                "success": False
            }

        # Update query status
        from sqlalchemy import select, update
        await db.execute(
            update(Query)
            .where(Query.id == query_id)
            .values(status=QueryStatus.PROCESSING)
        )
        await db.commit()

        # Prepare request for LLM server
        url = f"http://{server.host}:{server.port}/api/generate"
        headers = {
            "Content-Type": "application/json"
        }

        if server.api_key:
            headers["Authorization"] = f"Bearer {server.api_key}"

        payload = {
            "prompt": prompt,
            "model": model.name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stop": stop
        }

        # Send request to LLM server
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"LLM server error: HTTP {response.status_code} - {response.text}")

                # Update query with error
                await update_query_response(
                    db=db,
                    query_id=query_id,
                    response_text="",
                    token_count_prompt=0,
                    token_count_response=0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    status="failed",
                    error_message=f"LLM server error: HTTP {response.status_code}"
                )

                return {
                    "error": f"LLM server error: HTTP {response.status_code}",
                    "success": False
                }

            # Parse response
            result = response.json()

            if "error" in result:
                logger.error(f"LLM server returned error: {result['error']}")

                # Update query with error
                await update_query_response(
                    db=db,
                    query_id=query_id,
                    response_text="",
                    token_count_prompt=0,
                    token_count_response=0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    status="failed",
                    error_message=f"LLM server error: {result['error']}"
                )

                return {
                    "error": f"LLM server error: {result['error']}",
                    "success": False
                }

            # Extract response data
            response_text = result.get("response", "")
            prompt_tokens = result.get("prompt_tokens", 0)
            completion_tokens = result.get("completion_tokens", 0)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # ms

            # Update query with response
            await update_query_response(
                db=db,
                query_id=query_id,
                response_text=response_text,
                token_count_prompt=prompt_tokens,
                token_count_response=completion_tokens,
                processing_time_ms=processing_time,
                status="completed",
                cache_key=cache_key
            )

            # Add to semantic cache if enabled
            if self.semantic_cache and settings.ENABLE_SEMANTIC_CACHE:
                await self.semantic_cache.add(
                    prompt=prompt,
                    response=response_text,
                    model_id=model.id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cache_key=cache_key
                )

            # Return successful response
            return {
                "response": response_text,
                "model": model.name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "processing_time_ms": processing_time,
                "query_id": query_id,
                "cached": False,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error during LLM inference: {str(e)}")

            # Update query with error
            await update_query_response(
                db=db,
                query_id=query_id,
                response_text="",
                token_count_prompt=0,
                token_count_response=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                status="failed",
                error_message=f"Error: {str(e)}"
            )

            return {
                "error": f"Error: {str(e)}",
                "success": False
            }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        from sqlalchemy import select

        models = []
        async with get_async_db_ctx() as db:
            result = await db.execute(select(LLMModel))
            for model in result.scalars().all():
                models.append({
                    "id": model.id,
                    "name": model.name,
                    "version": model.version,
                    "description": model.description,
                    "parameters": model.parameters,
                    "quantization": model.quantization,
                    "is_fine_tuned": model.is_fine_tuned,
                    "base_model": model.base_model
                })

        return models