import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Try to import FastAPI if it's available
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import RedirectResponse, JSONResponse
    import random
    
    from config import settings
    
    # Create FastAPI app
    app = FastAPI(
        title="Enterprise LLM Platform",
        description="On-premises LLM platform with multi-GPU load balancing and analytics",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Try to import API router if possible
    try:
        from api.router import router as api_router
        app.include_router(api_router, prefix="/api")
        logger.info("API router registered with FastAPI app")
    except ImportError as e:
        logger.warning(f"API router could not be imported: {str(e)}")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Setup templates
    templates = Jinja2Templates(directory="templates")
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://yourdomain.com"]  # Replace with your actual domain,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "app": "fastapi"}
    
    logger.info("FastAPI app initialized successfully")
    
except ImportError:
    # If FastAPI is not available, just log a message
    logger.info("FastAPI is not available, using Flask in main.py instead")
    
    # Import Flask app from main.py to provide a fallback
    try:
        from main import app
        logger.info("Flask app imported from main.py")
    except ImportError:
        logger.error("Could not import app from main.py")
        
        # Create a very minimal Flask app as last resort
        try:
            from flask import Flask, jsonify
            app = Flask(__name__)
            
            @app.route('/health')
            def health_check():
                return jsonify({"status": "healthy", "app": "minimal_flask"})
            
            logger.info("Created minimal Flask app as fallback")
        except ImportError:
            logger.error("Could not create fallback Flask app")
            # Leave app undefined
