import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from config import settings
from database import get_db
from schemas import LLMPromptRequest, LLMResponse, LLMModelInfo
from llm.inference import LLMInferenceManager
from models import User
from utils import get_current_user, verify_api_key
from auth.permissions import PermissionManager

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create inference manager
inference_manager = LLMInferenceManager()

# Create permission manager
permission_manager = PermissionManager()

@router.on_event("startup")
async def startup_event():
    await inference_manager.initialize()

@router.post("/generate", response_model=LLMResponse)
async def generate_text(
    request: Request,
    prompt_request: LLMPromptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate text from a prompt using the LLM
    """
    try:
        # Check if user can access the API
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_API_ACCESS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this API"
            )
        
        # Get client IP
        client_ip = request.client.host
        
        # Generate text
        result = await inference_manager.generate(
            prompt=prompt_request.prompt,
            model_name=prompt_request.model,
            max_tokens=prompt_request.max_tokens,
            temperature=prompt_request.temperature,
            top_p=prompt_request.top_p,
            frequency_penalty=prompt_request.frequency_penalty,
            presence_penalty=prompt_request.presence_penalty,
            stop=prompt_request.stop,
            user_id=current_user.id,
            source="api",
            client_ip=client_ip,
            metadata=prompt_request.metadata,
            db=db
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to generate text")
            )
        
        # Return response
        return LLMResponse(
            response=result["response"],
            model=result["model"],
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=result["total_tokens"],
            processing_time_ms=result["processing_time_ms"],
            created_at=result.get("created_at", datetime.utcnow()),
            query_id=result["query_id"],
            cached=result.get("cached", False)
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating text: {str(e)}"
        )

@router.post("/api-generate")
async def api_generate_text(
    request: Request,
    prompt_request: Dict[str, Any] = Body(...),
    api_key: str = Query(None),
    x_api_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Public API endpoint for generating text, authenticated with API key
    """
    try:
        # Check for API key
        if not api_key:
            # Try header
            x_api_key = request.headers.get("X-API-Key") or x_api_key
            
            if not x_api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API key required"
                )
            api_key = x_api_key
            
        # Verify API key
        user = await verify_api_key(api_key, db)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
            
        # Get client IP
        client_ip = request.client.host
        
        # Parse request
        try:
            # Create valid LLMPromptRequest
            validated_request = LLMPromptRequest(
                prompt=prompt_request.get("prompt", ""),
                model=prompt_request.get("model"),
                max_tokens=prompt_request.get("max_tokens", 1024),
                temperature=prompt_request.get("temperature", 0.7),
                top_p=prompt_request.get("top_p", 1.0),
                frequency_penalty=prompt_request.get("frequency_penalty", 0.0),
                presence_penalty=prompt_request.get("presence_penalty", 0.0),
                stop=prompt_request.get("stop"),
                metadata=prompt_request.get("metadata")
            )
        except ValidationError:
            raise HTTPException(
                status_code=422,
                detail="Invalid request parameters"
            )
            
        # Generate text
        result = await inference_manager.generate(
            prompt=validated_request.prompt,
            model_name=validated_request.model,
            max_tokens=validated_request.max_tokens,
            temperature=validated_request.temperature,
            top_p=validated_request.top_p,
            frequency_penalty=validated_request.frequency_penalty,
            presence_penalty=validated_request.presence_penalty,
            stop=validated_request.stop,
            user_id=user.id,
            source="api",
            client_ip=client_ip,
            metadata=validated_request.metadata,
            db=db
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to generate text")
            )
            
        # Return response
        return {
            "response": result["response"],
            "model": result["model"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "processing_time_ms": result["processing_time_ms"],
            "query_id": result["query_id"],
            "cached": result.get("cached", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in API generate text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating text: {str(e)}"
        )

@router.get("/models", response_model=List[LLMModelInfo])
async def get_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available LLM models
    """
    try:
        # Check if user can access the API
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_API_ACCESS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this API"
            )
            
        # Get models
        models = await inference_manager.get_available_models()
        
        # Convert to schema
        return [
            LLMModelInfo(
                id=model["id"],
                name=model["name"],
                version=model["version"],
                description=model["description"],
                parameters=model["parameters"],
                quantization=model["quantization"],
                is_fine_tuned=model["is_fine_tuned"],
                base_model=model["base_model"]
            )
            for model in models
        ]
        
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting models: {str(e)}"
        )

@router.get("/servers")
async def get_servers(
    current_user: User = Depends(get_current_user)
):
    """
    Get status of LLM servers
    """
    try:
        # Check if user has server management permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SERVER_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view server status"
            )
            
        # Get server status
        servers = await inference_manager.load_balancer.get_all_servers_status()
        
        return {
            "servers": servers
        }
        
    except Exception as e:
        logger.error(f"Error getting server status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting server status: {str(e)}"
        )

@router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get semantic cache statistics
    """
    try:
        # Check if user has server management permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SERVER_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view cache statistics"
            )
            
        # Check if semantic cache is enabled
        if not settings.ENABLE_SEMANTIC_CACHE or not inference_manager.semantic_cache:
            return {
                "enabled": False,
                "message": "Semantic cache is disabled"
            }
            
        # Get cache statistics
        stats = await inference_manager.semantic_cache.get_stats()
        
        return {
            "enabled": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cache statistics: {str(e)}"
        )

from datetime import datetime
