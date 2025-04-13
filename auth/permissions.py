import logging
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserRole
from utils import get_current_user

logger = logging.getLogger(__name__)

class PermissionManager:
    """Manager for role-based permissions"""
    
    # Permission constants
    PERMISSION_USER_MANAGEMENT = "user_management"
    PERMISSION_SERVER_MANAGEMENT = "server_management"
    PERMISSION_MODEL_MANAGEMENT = "model_management"
    PERMISSION_FINE_TUNING = "fine_tuning"
    PERMISSION_ANALYTICS = "analytics"
    PERMISSION_SYSTEM_CONFIG = "system_config"
    PERMISSION_API_ACCESS = "api_access"
    
    def __init__(self):
        # Define role-based permissions
        self.role_permissions = {
            UserRole.ADMIN: [
                self.PERMISSION_USER_MANAGEMENT,
                self.PERMISSION_SERVER_MANAGEMENT,
                self.PERMISSION_MODEL_MANAGEMENT,
                self.PERMISSION_FINE_TUNING,
                self.PERMISSION_ANALYTICS,
                self.PERMISSION_SYSTEM_CONFIG,
                self.PERMISSION_API_ACCESS
            ],
            UserRole.MANAGER: [
                self.PERMISSION_MODEL_MANAGEMENT,
                self.PERMISSION_FINE_TUNING,
                self.PERMISSION_ANALYTICS,
                self.PERMISSION_API_ACCESS
            ],
            UserRole.ANALYST: [
                self.PERMISSION_ANALYTICS,
                self.PERMISSION_API_ACCESS
            ],
            UserRole.USER: [
                self.PERMISSION_API_ACCESS
            ]
        }
        
    def get_user_permissions(self, user: User) -> List[str]:
        """Get a list of permissions for a user based on their role"""
        return self.role_permissions.get(user.role, [])
        
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if a user has a specific permission"""
        user_permissions = self.get_user_permissions(user)
        return permission in user_permissions
        
    def require_permission(self, permission: str):
        """Dependency for requiring a specific permission"""
        async def dependency(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            if not self.has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                )
            return current_user
        return dependency
        
    async def get_permission_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a summary of permissions for a user"""
        async with get_db() as db:
            from sqlalchemy import select
            
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            if not user:
                return {"error": "User not found"}
                
            # Get permissions
            permissions = self.get_user_permissions(user)
            
            return {
                "user_id": user.id,
                "username": user.username,
                "role": user.role.value,
                "permissions": permissions,
                "can_manage_users": self.PERMISSION_USER_MANAGEMENT in permissions,
                "can_manage_servers": self.PERMISSION_SERVER_MANAGEMENT in permissions,
                "can_manage_models": self.PERMISSION_MODEL_MANAGEMENT in permissions,
                "can_fine_tune": self.PERMISSION_FINE_TUNING in permissions,
                "can_view_analytics": self.PERMISSION_ANALYTICS in permissions,
                "can_configure_system": self.PERMISSION_SYSTEM_CONFIG in permissions,
                "can_access_api": self.PERMISSION_API_ACCESS in permissions
            }
