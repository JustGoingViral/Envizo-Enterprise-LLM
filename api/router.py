import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Try to import FastAPI components
    from fastapi import APIRouter
    
    # Create API router only if FastAPI is available
    router = APIRouter()
    
    try:
        # Selectively import endpoints that might not all be available
        from api.endpoints import llm, users, analytics, fine_tuning, openapi, focal_bi, system
        
        # Include all endpoint routers
        router.include_router(llm.router, prefix="/llm", tags=["LLM"])
        router.include_router(users.router, prefix="/auth", tags=["Authentication"])
        router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
        router.include_router(fine_tuning.router, prefix="/fine-tuning", tags=["Fine-Tuning"])
        router.include_router(openapi.router, prefix="/openapi", tags=["OpenAPI"])
        router.include_router(focal_bi.router, prefix="/focal-bi", tags=["Focal BI"])
        router.include_router(system.router, prefix="/system", tags=["System"])
        
        logger.info("API endpoints registered successfully with FastAPI")
    except ImportError as e:
        logger.warning(f"Some API endpoints could not be imported: {str(e)}")
        
except ImportError:
    # If FastAPI is not available, use a dummy router for Flask app
    logger.info("FastAPI not available, API endpoints will not be registered")
    
    class DummyRouter:
        def include_router(self, *args, **kwargs):
            pass
    
    router = DummyRouter()
