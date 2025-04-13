import logging
import os
import json
import shutil
import asyncio
import aiofiles
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from config import settings
from database import get_db
from models import User, SystemBackup
from utils import get_current_user
from auth.permissions import PermissionManager
from schemas import SystemBackup as SystemBackupSchema

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create permission manager
permission_manager = PermissionManager()

@router.get("/config")
async def get_system_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get system configuration
    """
    try:
        # Check if user has system config permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SYSTEM_CONFIG):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view system configuration"
            )
            
        # Return config (excluding sensitive values)
        return {
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "llm_default_model": settings.LLM_DEFAULT_MODEL,
            "llm_endpoint_url": settings.LLM_ENDPOINT_URL,
            "llm_request_timeout": settings.LLM_REQUEST_TIMEOUT,
            "enable_load_balancing": settings.ENABLE_LOAD_BALANCING,
            "load_balancer_strategy": settings.LOAD_BALANCER_STRATEGY,
            "enable_semantic_cache": settings.ENABLE_SEMANTIC_CACHE,
            "semantic_cache_expiry_seconds": settings.SEMANTIC_CACHE_EXPIRY_SECONDS,
            "semantic_cache_similarity_threshold": settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
            "fine_tuning_output_dir": settings.FINE_TUNING_OUTPUT_DIR,
            "tabby_ml_enabled": bool(settings.TABBY_ML_ENDPOINT),
            "focal_bi_enabled": bool(settings.FOCAL_BI_ENDPOINT),
            "server_count": len(settings.LLM_SERVERS)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting system config: {str(e)}"
        )

@router.post("/backup")
async def create_backup(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    backup_type: str = Form("full"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a system backup
    """
    try:
        # Check if user has system config permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SYSTEM_CONFIG):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to manage system backups"
            )
            
        # Validate backup type
        valid_types = ["full", "models", "database", "config"]
        if backup_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backup type. Allowed: {', '.join(valid_types)}"
            )
            
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join("backups", datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup info file
        backup_info = {
            "name": name,
            "description": description,
            "backup_type": backup_type,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user.username,
            "app_version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }
        
        backup_info_path = os.path.join(backup_dir, "backup_info.json")
        async with aiofiles.open(backup_info_path, "w") as f:
            await f.write(json.dumps(backup_info, indent=2))
            
        # Initialize background backup task
        asyncio.create_task(
            perform_backup(
                backup_dir=backup_dir,
                backup_type=backup_type,
                user_id=current_user.id,
                name=name,
                description=description
            )
        )
        
        # Create backup record
        backup = SystemBackup(
            name=name,
            description=description,
            backup_path=backup_dir,
            created_by_id=current_user.id,
            backup_type=backup_type,
            status="in_progress"
        )
        
        db.add(backup)
        await db.commit()
        await db.refresh(backup)
        
        return {
            "id": backup.id,
            "name": backup.name,
            "backup_path": backup.backup_path,
            "backup_type": backup.backup_type,
            "status": backup.status,
            "created_at": backup.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating backup: {str(e)}"
        )

async def perform_backup(
    backup_dir: str,
    backup_type: str,
    user_id: int,
    name: str,
    description: Optional[str] = None
):
    """Background task to perform backup"""
    try:
        logger.info(f"Starting {backup_type} backup to {backup_dir}")
        
        # In a real implementation, this would backup the actual data
        # For this implementation, we'll just create placeholder files
        
        if backup_type in ["full", "database"]:
            # Backup database
            db_backup_path = os.path.join(backup_dir, "database.sql")
            async with aiofiles.open(db_backup_path, "w") as f:
                await f.write("-- Database backup placeholder\n")
                
        if backup_type in ["full", "models"]:
            # Backup models
            models_dir = os.path.join(backup_dir, "models")
            os.makedirs(models_dir, exist_ok=True)
            
            model_info_path = os.path.join(models_dir, "model_info.json")
            async with aiofiles.open(model_info_path, "w") as f:
                await f.write(json.dumps({"models": ["mistral-7b", "llama-3-8b"]}, indent=2))
                
        if backup_type in ["full", "config"]:
            # Backup config
            config_path = os.path.join(backup_dir, "config.json")
            async with aiofiles.open(config_path, "w") as f:
                config_data = {
                    "app_name": settings.APP_NAME,
                    "environment": settings.ENVIRONMENT,
                    "debug": settings.DEBUG,
                    "llm_default_model": settings.LLM_DEFAULT_MODEL,
                    "enable_load_balancing": settings.ENABLE_LOAD_BALANCING,
                    "load_balancer_strategy": settings.LOAD_BALANCER_STRATEGY,
                    "enable_semantic_cache": settings.ENABLE_SEMANTIC_CACHE
                }
                await f.write(json.dumps(config_data, indent=2))
                
        # Simulate backup time
        await asyncio.sleep(5)
        
        # Update backup record
        async with get_db() as db:
            from sqlalchemy import select, update
            
            stmt = select(SystemBackup).where(
                SystemBackup.backup_path == backup_dir,
                SystemBackup.created_by_id == user_id
            )
            result = await db.execute(stmt)
            backup = result.scalars().first()
            
            if backup:
                # Calculate size
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(backup_dir):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
                        
                # Update backup record
                backup.status = "completed"
                backup.size_bytes = total_size
                await db.commit()
                
        logger.info(f"Backup completed: {backup_dir}")
        
    except Exception as e:
        logger.error(f"Error during backup: {str(e)}")
        
        # Update backup record to failed status
        try:
            async with get_db() as db:
                from sqlalchemy import select, update
                
                stmt = select(SystemBackup).where(
                    SystemBackup.backup_path == backup_dir,
                    SystemBackup.created_by_id == user_id
                )
                result = await db.execute(stmt)
                backup = result.scalars().first()
                
                if backup:
                    backup.status = "failed"
                    await db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update backup status: {str(update_error)}")

@router.get("/backups", response_model=List[SystemBackupSchema])
async def list_backups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all system backups
    """
    try:
        # Check if user has system config permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SYSTEM_CONFIG):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view system backups"
            )
            
        # Get all backups
        from sqlalchemy import select
        
        stmt = select(SystemBackup).order_by(SystemBackup.created_at.desc())
        result = await db.execute(stmt)
        backups = result.scalars().all()
        
        # Convert to schema
        return [
            SystemBackupSchema(
                id=backup.id,
                name=backup.name,
                description=backup.description,
                backup_path=backup.backup_path,
                size_bytes=backup.size_bytes,
                created_at=backup.created_at,
                created_by_id=backup.created_by_id,
                backup_type=backup.backup_type,
                status=backup.status
            )
            for backup in backups
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing backups: {str(e)}"
        )

@router.get("/backups/{backup_id}", response_model=SystemBackupSchema)
async def get_backup(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a system backup by ID
    """
    try:
        # Check if user has system config permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SYSTEM_CONFIG):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view system backups"
            )
            
        # Get backup
        from sqlalchemy import select
        
        stmt = select(SystemBackup).where(SystemBackup.id == backup_id)
        result = await db.execute(stmt)
        backup = result.scalars().first()
        
        if not backup:
            raise HTTPException(
                status_code=404,
                detail=f"Backup with ID {backup_id} not found"
            )
            
        return SystemBackupSchema(
            id=backup.id,
            name=backup.name,
            description=backup.description,
            backup_path=backup.backup_path,
            size_bytes=backup.size_bytes,
            created_at=backup.created_at,
            created_by_id=backup.created_by_id,
            backup_type=backup.backup_type,
            status=backup.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting backup: {str(e)}"
        )

@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore a system backup
    """
    try:
        # Check if user has system config permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SYSTEM_CONFIG):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to restore system backups"
            )
            
        # Get backup
        from sqlalchemy import select
        
        stmt = select(SystemBackup).where(SystemBackup.id == backup_id)
        result = await db.execute(stmt)
        backup = result.scalars().first()
        
        if not backup:
            raise HTTPException(
                status_code=404,
                detail=f"Backup with ID {backup_id} not found"
            )
            
        # Check backup status
        if backup.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot restore backup with status: {backup.status}"
            )
            
        # Check if backup path exists
        if not os.path.exists(backup.backup_path):
            raise HTTPException(
                status_code=400,
                detail=f"Backup directory not found: {backup.backup_path}"
            )
            
        # Initialize background restore task
        asyncio.create_task(
            perform_restore(
                backup_path=backup.backup_path,
                backup_type=backup.backup_type,
                backup_id=backup_id
            )
        )
        
        return {
            "message": f"Restore of backup '{backup.name}' initiated",
            "backup_id": backup_id,
            "status": "in_progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error restoring backup: {str(e)}"
        )

async def perform_restore(
    backup_path: str,
    backup_type: str,
    backup_id: int
):
    """Background task to perform restore"""
    try:
        logger.info(f"Starting restore from backup {backup_id} ({backup_path})")
        
        # In a real implementation, this would restore the actual data
        # For this implementation, we'll just simulate a restore
        
        # Simulate restore time
        await asyncio.sleep(10)
        
        logger.info(f"Restore completed from backup {backup_id}")
        
    except Exception as e:
        logger.error(f"Error during restore: {str(e)}")

@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a system backup
    """
    try:
        # Check if user has system config permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_SYSTEM_CONFIG):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete system backups"
            )
            
        # Get backup
        from sqlalchemy import select, delete
        
        stmt = select(SystemBackup).where(SystemBackup.id == backup_id)
        result = await db.execute(stmt)
        backup = result.scalars().first()
        
        if not backup:
            raise HTTPException(
                status_code=404,
                detail=f"Backup with ID {backup_id} not found"
            )
            
        # Delete backup directory if it exists
        if os.path.exists(backup.backup_path):
            shutil.rmtree(backup.backup_path)
            
        # Delete backup record
        stmt = delete(SystemBackup).where(SystemBackup.id == backup_id)
        await db.execute(stmt)
        await db.commit()
        
        return {"message": f"Backup '{backup.name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting backup: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Get system health status
    """
    try:
        # Check database connection
        db_healthy = True
        try:
            async with get_db() as db:
                from sqlalchemy import text
                await db.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_healthy = False
            
        # Check disk space
        disk_space = shutil.disk_usage("/")
        disk_percent_free = disk_space.free / disk_space.total * 100
        disk_healthy = disk_percent_free > 10  # Consider healthy if more than 10% free
        
        # Return health status
        return {
            "status": "healthy" if (db_healthy and disk_healthy) else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy"
                },
                "disk": {
                    "status": "healthy" if disk_healthy else "low_space",
                    "total_gb": disk_space.total / (1024 ** 3),
                    "free_gb": disk_space.free / (1024 ** 3),
                    "percent_free": disk_percent_free
                },
                "llm_servers": {
                    "status": "configured",
                    "count": len(settings.LLM_SERVERS)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
