import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

from config import settings
from database import get_db
from models import User, UserRole, ApiKey
from utils import get_password_hash, verify_password, create_access_token

logger = logging.getLogger(__name__)

class UserManager:
    """Manager for user operations"""
    
    def __init__(self):
        pass
        
    async def authenticate_user(
        self,
        username: str,
        password: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user with username and password"""
        from sqlalchemy import select
        
        # First try to find user by username
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            # Try by email
            stmt = select(User).where(User.email == username)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
        if not user:
            logger.warning(f"Authentication failed: User {username} not found")
            return None
            
        if not user.is_active:
            logger.warning(f"Authentication failed: User {username} is inactive")
            return None
            
        # Verify password
        if not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: Invalid password for user {username}")
            return None
            
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value
            }
        }
        
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        db: Optional[AsyncSession] = None
    ) -> User:
        """Create a new user"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.create_user(
                    username=username,
                    email=email,
                    password=password,
                    full_name=full_name,
                    role=role,
                    db=db
                )
                
        # Check if username already exists
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
            
        # Check if email already exists
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
            
        # Hash password
        hashed_password = get_password_hash(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=hashed_password,
            role=role
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created user {username} with role {role.value}")
        return user
        
    async def update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[User]:
        """Update a user"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.update_user(
                    user_id=user_id,
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=role,
                    is_active=is_active,
                    db=db
                )
                
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return None
            
        # Update fields
        if username is not None:
            # Check if username is already taken
            if username != user.username:
                stmt = select(User).where(User.username == username)
                result = await db.execute(stmt)
                if result.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
            user.username = username
            
        if email is not None:
            # Check if email is already taken
            if email != user.email:
                stmt = select(User).where(User.email == email)
                result = await db.execute(stmt)
                if result.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
            user.email = email
            
        if full_name is not None:
            user.full_name = full_name
            
        if role is not None:
            user.role = role
            
        if is_active is not None:
            user.is_active = is_active
            
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Updated user {user.username}")
        return user
        
    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Change a user's password"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.change_password(
                    user_id=user_id,
                    current_password=current_password,
                    new_password=new_password,
                    db=db
                )
                
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return False
            
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return False
            
        # Hash new password
        user.password_hash = get_password_hash(new_password)
        
        await db.commit()
        logger.info(f"Changed password for user {user.username}")
        return True
        
    async def reset_password(
        self,
        user_id: int,
        new_password: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Reset a user's password (admin function)"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.reset_password(
                    user_id=user_id,
                    new_password=new_password,
                    db=db
                )
                
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return False
            
        # Hash new password
        user.password_hash = get_password_hash(new_password)
        
        await db.commit()
        logger.info(f"Reset password for user {user.username}")
        return True
        
    async def delete_user(
        self,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Delete a user"""
        from sqlalchemy import select, delete
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.delete_user(
                    user_id=user_id,
                    db=db
                )
                
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return False
            
        # Delete user
        stmt = delete(User).where(User.id == user_id)
        await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Deleted user {user.username}")
        return True
        
    async def get_user(
        self,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> Optional[User]:
        """Get a user by ID"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.get_user(
                    user_id=user_id,
                    db=db
                )
                
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalars().first()
        
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        db: Optional[AsyncSession] = None
    ) -> List[User]:
        """Get a list of users"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.get_users(
                    skip=skip,
                    limit=limit,
                    role=role,
                    is_active=is_active,
                    db=db
                )
                
        # Build query
        query = select(User)
        
        if role is not None:
            query = query.where(User.role == role)
            
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        return list(result.scalars().all())
        
    async def create_api_key(
        self,
        user_id: int,
        name: str,
        expires_at: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[ApiKey]:
        """Create a new API key for a user"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.create_api_key(
                    user_id=user_id,
                    name=name,
                    expires_at=expires_at,
                    db=db
                )
                
        # Check if user exists
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return None
            
        # Generate API key
        key = secrets.token_hex(32)
        
        # Create API key
        api_key = ApiKey(
            key=key,
            name=name,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        
        logger.info(f"Created API key '{name}' for user {user.username}")
        return api_key
        
    async def get_api_keys(
        self,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> List[ApiKey]:
        """Get API keys for a user"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.get_api_keys(
                    user_id=user_id,
                    db=db
                )
                
        # Get API keys
        stmt = select(ApiKey).where(ApiKey.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
        
    async def revoke_api_key(
        self,
        key_id: int,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Revoke an API key"""
        from sqlalchemy import select
        
        # Create DB session if not provided
        if db is None:
            async with get_db() as db:
                return await self.revoke_api_key(
                    key_id=key_id,
                    db=db
                )
                
        # Get API key
        stmt = select(ApiKey).where(ApiKey.id == key_id)
        result = await db.execute(stmt)
        api_key = result.scalars().first()
        
        if not api_key:
            return False
            
        # Revoke API key
        api_key.is_active = False
        await db.commit()
        
        logger.info(f"Revoked API key {api_key.name}")
        return True
