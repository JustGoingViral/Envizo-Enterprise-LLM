import logging
import os
import json
import hashlib
import aiofiles
import httpx
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, get_async_db
from models import User, UserRole, ApiKey, Query, QueryStatus, ServerNode, LLMModel

# Setup logging
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# JWT configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
    except jwt.JWTError:
        raise credentials_exception
        
    # Find user in database
    user = await get_user_by_username(db, username)
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
        
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if the current authenticated user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if the current user has admin privileges"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

async def verify_api_key(
    api_key: str, 
    db: AsyncSession
) -> Optional[User]:
    """Verify an API key and return the associated user"""
    from sqlalchemy import select
    
    # Query the API key
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key == api_key,
            ApiKey.is_active == True
        )
    )
    api_key_obj = result.scalars().first()
    
    if not api_key_obj:
        return None
        
    # Check if the API key has expired
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        return None
        
    # Get the user associated with the API key
    result = await db.execute(
        select(User).where(
            User.id == api_key_obj.user_id,
            User.is_active == True
        )
    )
    user = result.scalars().first()
    
    return user

async def get_user_by_username(
    db: AsyncSession, 
    username: str
) -> Optional[User]:
    """Get a user by username"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalars().first()

async def get_user_by_email(
    db: AsyncSession, 
    email: str
) -> Optional[User]:
    """Get a user by email"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalars().first()

async def log_query(
    db: AsyncSession,
    user_id: Optional[int],
    model_id: int,
    query_text: str,
    source: str = "web_ui",
    client_ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Log a query to the database and return the query ID"""
    from models import Query, QuerySource, QueryStatus
    
    # Create query record
    query = Query(
        user_id=user_id,
        model_id=model_id,
        query_text=query_text,
        status=QueryStatus.PENDING,
        source=getattr(QuerySource, source.upper(), QuerySource.API),
        client_ip=client_ip,
        query_metadata=metadata
    )
    
    # Add to database
    db.add(query)
    await db.commit()
    await db.refresh(query)
    
    return query.id

async def update_query_response(
    db: AsyncSession,
    query_id: int,
    response_text: str,
    token_count_prompt: int,
    token_count_response: int,
    processing_time_ms: float,
    status: str = "completed",
    cached: bool = False,
    cache_key: Optional[str] = None,
    error_message: Optional[str] = None
) -> None:
    """Update a query with its response"""
    from sqlalchemy import select
    
    # Get the query
    result = await db.execute(
        select(Query).where(Query.id == query_id)
    )
    query = result.scalars().first()
    
    if not query:
        logger.error(f"Query with ID {query_id} not found")
        return
        
    # Update query fields
    query.response_text = response_text
    query.status = getattr(QueryStatus, status.upper(), QueryStatus.COMPLETED)
    query.token_count_prompt = token_count_prompt
    query.token_count_response = token_count_response
    query.processing_time_ms = processing_time_ms
    query.completed_at = datetime.utcnow()
    query.cached = cached
    
    if cache_key:
        query.cache_key = cache_key
        
    if error_message:
        query.error_message = error_message
        
    # Update in database
    await db.commit()

def compute_cache_key(prompt: str, model: str) -> str:
    """Compute a cache key for a prompt and model"""
    # Create a hash for the prompt and model
    hash_input = f"{prompt}:{model}"
    cache_key = hashlib.md5(hash_input.encode()).hexdigest()
    return cache_key

async def check_server_health(server: ServerNode) -> Tuple[bool, str]:
    """Check the health of an LLM server node"""
    try:
        url = f"http://{server.host}:{server.port}/health"
        headers = {}
        
        if server.api_key:
            headers["Authorization"] = f"Bearer {server.api_key}"
            
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            
        if response.status_code == 200:
            return True, "healthy"
        else:
            return False, f"Unhealthy: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

async def update_server_health(db: AsyncSession, server_id: int, status: str) -> None:
    """Update the health status of a server node"""
    from sqlalchemy import select
    
    # Get the server
    result = await db.execute(
        select(ServerNode).where(ServerNode.id == server_id)
    )
    server = result.scalars().first()
    
    if not server:
        logger.error(f"Server with ID {server_id} not found")
        return
        
    # Update server health
    server.health_status = status
    server.last_health_check = datetime.utcnow()
    
    # Update in database
    await db.commit()

async def get_server_load_metrics(server: ServerNode) -> Dict[str, Any]:
    """Get load metrics from an LLM server node"""
    try:
        url = f"http://{server.host}:{server.port}/metrics"
        headers = {}
        
        if server.api_key:
            headers["Authorization"] = f"Bearer {server.api_key}"
            
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            
        if response.status_code == 200:
            metrics = response.json()
            return metrics
        else:
            logger.error(f"Failed to get server metrics: HTTP {response.status_code}")
            return {
                "gpu_utilization": 0.0,
                "gpu_memory_used": 0.0,
                "gpu_memory_total": server.gpu_memory,
                "cpu_utilization": 0.0,
                "active_requests": 0,
                "queue_depth": 0
            }
            
    except Exception as e:
        logger.error(f"Error getting server metrics: {str(e)}")
        return {
            "gpu_utilization": 0.0,
            "gpu_memory_used": 0.0,
            "gpu_memory_total": server.gpu_memory,
            "cpu_utilization": 0.0,
            "active_requests": 0,
            "queue_depth": 0
        }

async def load_initial_data() -> None:
    """Load initial data into the database"""
    logger.info("Loading initial data...")
    
    # Create admin user if it doesn't exist
    from sqlalchemy import select
    
    try:
        # Use the async database session
        async for db in get_async_db():
            # Check if admin user exists
            result = await db.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = result.scalars().first()
            
            if not admin_user:
                # Create admin user
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    full_name="Administrator",
                    password_hash=get_password_hash("admin"),  # Default password, should be changed
                    role=UserRole.ADMIN
                )
                db.add(admin_user)
                await db.commit()
                logger.info("Created admin user")
                
            # Add default LLM models
            result = await db.execute(
                select(LLMModel).where(LLMModel.name == "mistral-7b")
            )
            default_model = result.scalars().first()
            
            if not default_model:
                # Add default models
                models = [
                    LLMModel(
                        name="mistral-7b",
                        version="1.0",
                        description="Mistral 7B base model",
                        parameters=7000000000,
                        quantization="int8",
                        is_fine_tuned=False
                    ),
                    LLMModel(
                        name="llama-3-8b",
                        version="1.0",
                        description="LLaMa 3 8B base model",
                        parameters=8000000000,
                        quantization="int8",
                        is_fine_tuned=False
                    )
                ]
                
                for model in models:
                    db.add(model)
                    
                await db.commit()
                logger.info("Added default LLM models")
                
            # Add default server node
            result = await db.execute(
                select(ServerNode).where(ServerNode.name == "default-gpu-server")
            )
            default_server = result.scalars().first()
            
            if not default_server:
                # Use server from settings
                server_config = settings.LLM_SERVERS[0]
                server = ServerNode(
                    name=server_config.get("name", "default-gpu-server"),
                    host=server_config.get("url", "localhost").replace("http://", "").split("/")[0].split(":")[0],
                    port=int(server_config.get("url", "http://localhost:8080").replace("http://", "").split("/")[0].split(":")[1] if ":" in server_config.get("url", "http://localhost:8080").replace("http://", "").split("/")[0] else 8080),
                    api_key=server_config.get("api_key"),
                    gpu_count=1,
                    gpu_memory=server_config.get("gpu_memory", 24),
                    is_active=True,
                    health_status="unknown"
                )
                db.add(server)
                await db.commit()
                logger.info("Added default server node")
            
            # Break after processing with the first session
            break
    except Exception as e:
        logger.error(f"Error loading initial data: {str(e)}")
        
    logger.info("Initial data loading completed")
