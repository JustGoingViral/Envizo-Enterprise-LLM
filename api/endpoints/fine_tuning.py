import logging
import os
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import aiofiles

from database import get_db
from config import settings
from models import User, LLMModel, FineTuningJob, FineTuningJobStatus
from utils import get_current_user
from auth.permissions import PermissionManager
from llm.fine_tuning import FineTuningManager
from schemas import FineTuningJobCreate, FineTuningJob as FineTuningJobSchema

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create fine-tuning manager
fine_tuning_manager = FineTuningManager()

# Create permission manager
permission_manager = PermissionManager()

@router.on_event("startup")
async def startup_event():
    await fine_tuning_manager.initialize()

@router.get("/models")
async def get_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get models available for fine-tuning
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Get models
        from sqlalchemy import select
        
        stmt = select(LLMModel).where(LLMModel.is_fine_tuned == False)
        result = await db.execute(stmt)
        models = result.scalars().all()
        
        return {
            "models": [
                {
                    "id": model.id,
                    "name": model.name,
                    "description": model.description,
                    "parameters": model.parameters,
                    "quantization": model.quantization
                }
                for model in models
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting models: {str(e)}"
        )

@router.post("/upload-training-file")
async def upload_training_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a training file for fine-tuning
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Check file size (limit to 100MB)
        if file.size > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File too large (max 100MB)"
            )
            
        # Check file extension
        allowed_extensions = [".jsonl", ".json", ".txt", ".csv"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
            
        # Create user directory if it doesn't exist
        user_dir = os.path.join(settings.FINE_TUNING_OUTPUT_DIR, f"user_{current_user.id}")
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(user_dir, filename)
        
        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
            
        # Return file info
        return {
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": len(content),
            "content_type": file.content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading training file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading training file: {str(e)}"
        )

@router.post("/jobs", response_model=FineTuningJobSchema)
async def create_fine_tuning_job(
    job_create: FineTuningJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new fine-tuning job
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Check if base model exists
        from sqlalchemy import select
        
        stmt = select(LLMModel).where(LLMModel.id == job_create.base_model_id)
        result = await db.execute(stmt)
        base_model = result.scalars().first()
        
        if not base_model:
            raise HTTPException(
                status_code=404,
                detail=f"Base model with ID {job_create.base_model_id} not found"
            )
            
        # Check if training file exists
        if not os.path.exists(job_create.training_file):
            raise HTTPException(
                status_code=400,
                detail=f"Training file not found: {job_create.training_file}"
            )
            
        # Check if validation file exists if provided
        if job_create.validation_file and not os.path.exists(job_create.validation_file):
            raise HTTPException(
                status_code=400,
                detail=f"Validation file not found: {job_create.validation_file}"
            )
            
        # Create job
        job_id = await fine_tuning_manager.create_job(
            name=job_create.name,
            base_model_id=job_create.base_model_id,
            user_id=current_user.id,
            training_file=job_create.training_file,
            validation_file=job_create.validation_file,
            description=job_create.description,
            hyperparameters=job_create.hyperparameters,
            output_model_name=job_create.output_model_name
        )
        
        # Get job details
        job = await fine_tuning_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=500,
                detail="Failed to create fine-tuning job"
            )
            
        # Convert to schema
        return FineTuningJobSchema(
            id=job["id"],
            name=job["name"],
            user_id=job["user_id"],
            base_model_id=job["base_model"]["id"],
            status=job["status"],
            description=job["description"],
            training_file=job["training_file"],
            validation_file=job["validation_file"],
            hyperparameters=job["hyperparameters"],
            metrics=job["metrics"],
            output_model_name=job["output_model_name"],
            created_at=datetime.fromisoformat(job["created_at"]),
            started_at=datetime.fromisoformat(job["started_at"]) if job["started_at"] else None,
            completed_at=datetime.fromisoformat(job["completed_at"]) if job["completed_at"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fine-tuning job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating fine-tuning job: {str(e)}"
        )

@router.get("/jobs")
async def list_fine_tuning_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List fine-tuning jobs
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Check status enum if provided
        if status:
            try:
                status_enum = FineTuningJobStatus[status.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )
                
        # Get jobs
        if permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT):
            # Admins can see all jobs
            jobs = await fine_tuning_manager.list_jobs(
                status=status,
                limit=limit,
                offset=offset
            )
        else:
            # Regular users can only see their own jobs
            jobs = await fine_tuning_manager.list_jobs(
                user_id=current_user.id,
                status=status,
                limit=limit,
                offset=offset
            )
            
        return {
            "jobs": jobs,
            "limit": limit,
            "offset": offset,
            "total": len(jobs)  # This is not accurate for pagination but works for now
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing fine-tuning jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing fine-tuning jobs: {str(e)}"
        )

@router.get("/jobs/{job_id}")
async def get_fine_tuning_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get fine-tuning job details
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Get job
        job = await fine_tuning_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Fine-tuning job with ID {job_id} not found"
            )
            
        # Check if user is allowed to view this job
        if job["user_id"] != current_user.id and not permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this job"
            )
            
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fine-tuning job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting fine-tuning job: {str(e)}"
        )

@router.post("/jobs/{job_id}/cancel")
async def cancel_fine_tuning_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a fine-tuning job
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Get job
        job = await fine_tuning_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Fine-tuning job with ID {job_id} not found"
            )
            
        # Check if user is allowed to cancel this job
        if job["user_id"] != current_user.id and not permission_manager.has_permission(current_user, permission_manager.PERMISSION_USER_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to cancel this job"
            )
            
        # Check if job can be cancelled
        if job["status"] not in ["queued", "preparing", "running"]:
            raise HTTPException(
                status_code=400,
                detail=f"Job with status '{job['status']}' cannot be cancelled"
            )
            
        # Cancel job
        success = await fine_tuning_manager.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to cancel job"
            )
            
        return {"message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling fine-tuning job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling fine-tuning job: {str(e)}"
        )

@router.get("/hyperparameter-suggestions")
async def get_hyperparameter_suggestions(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get suggested hyperparameters for a model
    """
    try:
        # Check if user has fine-tuning permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_FINE_TUNING):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access fine-tuning features"
            )
            
        # Check if model exists
        from sqlalchemy import select
        
        stmt = select(LLMModel).where(LLMModel.id == model_id)
        result = await db.execute(stmt)
        model = result.scalars().first()
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model with ID {model_id} not found"
            )
            
        # Return suggested hyperparameters based on model
        if "mistral" in model.name.lower():
            return {
                "suggested_hyperparameters": {
                    "learning_rate": 1e-5,
                    "epochs": 3,
                    "batch_size": 8,
                    "weight_decay": 0.01,
                    "warmup_steps": 100,
                    "lora_rank": 8,
                    "lora_alpha": 32,
                    "lora_dropout": 0.05
                }
            }
        elif "llama" in model.name.lower():
            return {
                "suggested_hyperparameters": {
                    "learning_rate": 2e-5,
                    "epochs": 3,
                    "batch_size": 4,
                    "weight_decay": 0.01,
                    "warmup_steps": 100,
                    "lora_rank": 16,
                    "lora_alpha": 32,
                    "lora_dropout": 0.05
                }
            }
        else:
            return {
                "suggested_hyperparameters": {
                    "learning_rate": 1e-5,
                    "epochs": 3,
                    "batch_size": 8,
                    "weight_decay": 0.01,
                    "warmup_steps": 100,
                    "lora_rank": 8,
                    "lora_alpha": 32,
                    "lora_dropout": 0.05
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hyperparameter suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting hyperparameter suggestions: {str(e)}"
        )
