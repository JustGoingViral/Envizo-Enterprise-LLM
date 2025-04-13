import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from database import get_db
from schemas import (
    User, UserCreate, UserUpdate, LoginRequest, 
    Token, ApiKey, ApiKeyCreate
)
from models import UserRole, User as UserModel
from utils import get_current_user, get_admin_user
from auth.users import UserManager
from auth.permissions import PermissionManager

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create user manager
user_manager = UserManager()

# Create permission manager
permission_manager = PermissionManager()

@router.post("/login", response_model=Token)
async def login(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login to get access token
    """
    try:
        # Authenticate user
        result = await user_manager.authenticate_user(
            username=login_request.username,
            password=login_request.password,
            db=db
        )
        
        if not result:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )
            
        return {
            "access_token": result["access_token"],
            "token_type": result["token_type"]
        }
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login error: {str(e)}"
        )

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get current user info
    """
    return User(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.get("/permissions")
async def get_user_permissions(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get user permissions
    """
    return {
        "permissions": permission_manager.get_user_permissions(current_user)
    }

@router.post("/users", response_model=User)
async def create_user(
    user_create: UserCreate,
    current_user: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user (admin only)
    """
    try:
        # Create user
        user = await user_manager.create_user(
            username=user_create.username,
            email=user_create.email,
            password=user_create.password,
            full_name=user_create.full_name,
            role=UserRole[user_create.role.upper()],
            db=db
        )
        
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating user: {str(e)}"
        )

@router.get("/users", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get users (admin only)
    """
    try:
        # Check if user has permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
            
        # Convert role string to enum if provided
        role_enum = None
        if role:
            try:
                role_enum = UserRole[role.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid role: {role}"
                )
                
        # Get users
        users = await user_manager.get_users(
            skip=skip,
            limit=limit,
            role=role_enum,
            is_active=is_active,
            db=db
        )
        
        # Convert to schema
        return [
            User(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting users: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID
    """
    try:
        # Check if user has permission or is getting their own info
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT) and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
            
        # Get user
        user = await user_manager.get_user(
            user_id=user_id,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting user: {str(e)}"
        )

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user
    """
    try:
        # Check if user has permission or is updating their own info
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT) and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
            
        # If user is updating role or active status, must be admin
        if (user_update.role is not None or user_update.is_active is not None) and not permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="Only admins can update role or active status"
            )
            
        # Convert role string to enum if provided
        role_enum = None
        if user_update.role:
            try:
                role_enum = UserRole[user_update.role.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid role: {user_update.role}"
                )
                
        # Update user
        user = await user_manager.update_user(
            user_id=user_id,
            username=user_update.username,
            email=user_update.email,
            full_name=user_update.full_name,
            role=role_enum,
            is_active=user_update.is_active,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating user: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user (admin only)
    """
    try:
        # Prevent deletion of own account
        if current_user.id == user_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account"
            )
            
        # Delete user
        success = await user_manager.delete_user(
            user_id=user_id,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting user: {str(e)}"
        )

@router.post("/change-password")
async def change_password(
    current_password: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Change password
        success = await user_manager.change_password(
            user_id=current_user.id,
            current_password=current_password,
            new_password=new_password,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Incorrect current password"
            )
            
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error changing password: {str(e)}"
        )

@router.post("/reset-password/{user_id}")
async def reset_password(
    user_id: int,
    new_password: str = Body(..., embed=True),
    current_user: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset user password (admin only)
    """
    try:
        # Reset password
        success = await user_manager.reset_password(
            user_id=user_id,
            new_password=new_password,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting password: {str(e)}"
        )

@router.post("/api-keys", response_model=ApiKey)
async def create_api_key(
    api_key_create: ApiKeyCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key for the current user
    """
    try:
        # Create API key
        api_key = await user_manager.create_api_key(
            user_id=current_user.id,
            name=api_key_create.name,
            expires_at=api_key_create.expires_at,
            db=db
        )
        
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="Failed to create API key"
            )
            
        return ApiKey(
            id=api_key.id,
            key=api_key.key,
            name=api_key.name,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating API key: {str(e)}"
        )

@router.get("/api-keys", response_model=List[ApiKey])
async def get_api_keys(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get API keys for the current user
    """
    try:
        # Get API keys
        api_keys = await user_manager.get_api_keys(
            user_id=current_user.id,
            db=db
        )
        
        # Convert to schema
        return [
            ApiKey(
                id=api_key.id,
                key=api_key.key,
                name=api_key.name,
                is_active=api_key.is_active,
                created_at=api_key.created_at,
                expires_at=api_key.expires_at
            )
            for api_key in api_keys
        ]
        
    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting API keys: {str(e)}"
        )

@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke an API key
    """
    try:
        # Revoke API key
        success = await user_manager.revoke_api_key(
            key_id=key_id,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="API key not found"
            )
            
        return {"message": "API key revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error revoking API key: {str(e)}"
        )
