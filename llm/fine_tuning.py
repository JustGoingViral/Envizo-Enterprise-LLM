import os
import logging
import json
import aiofiles
import asyncio
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import FineTuningJob, FineTuningJobStatus, LLMModel, User

logger = logging.getLogger(__name__)

class FineTuningManager:
    """Manager for LLM fine-tuning jobs"""
    
    def __init__(self):
        self.output_dir = settings.FINE_TUNING_OUTPUT_DIR
        self.initialized = False
        self.active_jobs = {}  # Track currently running jobs
        
    async def initialize(self):
        """Initialize the fine-tuning manager"""
        if self.initialized:
            return
            
        logger.info("Initializing Fine-Tuning Manager")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Process any queued or running jobs from previous session
        await self._resume_jobs()
        
        # Start background task to process jobs
        asyncio.create_task(self.job_processing_loop())
        
        self.initialized = True
        logger.info("Fine-Tuning Manager initialized")
        
    async def _resume_jobs(self):
        """Resume any jobs that were in progress or queued"""
        async with get_db() as db:
            from sqlalchemy import select
            
            # Find jobs that are queued or running
            stmt = select(FineTuningJob).where(
                FineTuningJob.status.in_([
                    FineTuningJobStatus.QUEUED,
                    FineTuningJobStatus.PREPARING,
                    FineTuningJobStatus.RUNNING
                ])
            )
            
            result = await db.execute(stmt)
            jobs = result.scalars().all()
            
            for job in jobs:
                if job.status == FineTuningJobStatus.RUNNING:
                    # Set back to QUEUED to restart
                    job.status = FineTuningJobStatus.QUEUED
                    logger.info(f"Resuming fine-tuning job {job.id} (set back to QUEUED)")
                    
            await db.commit()
            
    async def job_processing_loop(self):
        """Background task to process fine-tuning jobs"""
        while True:
            try:
                await self._process_next_job()
                # Wait before checking for more jobs
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in job processing loop: {str(e)}")
                await asyncio.sleep(30)  # Longer wait on error
                
    async def _process_next_job(self):
        """Process the next queued fine-tuning job"""
        # First check if we're already at max concurrent jobs
        if len(self.active_jobs) >= 1:  # Only allow one concurrent job for now
            return
            
        async with get_db() as db:
            from sqlalchemy import select
            
            # Find the next queued job
            stmt = select(FineTuningJob).where(
                FineTuningJob.status == FineTuningJobStatus.QUEUED
            ).order_by(
                FineTuningJob.created_at
            )
            
            result = await db.execute(stmt)
            job = result.scalars().first()
            
            if not job:
                return  # No jobs to process
                
            # Mark job as preparing
            job.status = FineTuningJobStatus.PREPARING
            job.started_at = datetime.utcnow()
            await db.commit()
            
            # Start job in background task
            asyncio.create_task(self._run_fine_tuning_job(job.id))
            
    async def _run_fine_tuning_job(self, job_id: int):
        """Run a fine-tuning job"""
        logger.info(f"Starting fine-tuning job {job_id}")
        
        async with get_db() as db:
            from sqlalchemy import select
            
            # Get job details
            stmt = select(FineTuningJob).where(FineTuningJob.id == job_id)
            result = await db.execute(stmt)
            job = result.scalars().first()
            
            if not job:
                logger.error(f"Fine-tuning job {job_id} not found")
                return
                
            # Get base model
            stmt = select(LLMModel).where(LLMModel.id == job.base_model_id)
            result = await db.execute(stmt)
            base_model = result.scalars().first()
            
            if not base_model:
                logger.error(f"Base model {job.base_model_id} not found for job {job_id}")
                job.status = FineTuningJobStatus.FAILED
                job.metrics = {"error": "Base model not found"}
                await db.commit()
                return
                
            # Track job as active
            self.active_jobs[job_id] = {
                "id": job_id,
                "name": job.name,
                "base_model": base_model.name,
                "start_time": datetime.utcnow()
            }
            
            try:
                # Update job status to running
                job.status = FineTuningJobStatus.RUNNING
                await db.commit()
                
                # Prepare output directory
                job_dir = os.path.join(self.output_dir, f"job_{job_id}")
                os.makedirs(job_dir, exist_ok=True)
                
                # In a real implementation, this would actually run the fine-tuning process
                # For this implementation, we'll simulate fine-tuning
                
                # Simulate training steps
                steps = 10
                metrics = {"loss": [], "accuracy": []}
                
                for step in range(steps):
                    # Simulate training step
                    loss = 1.0 - (step / steps) * 0.7  # Decreasing loss
                    accuracy = 0.5 + (step / steps) * 0.4  # Increasing accuracy
                    
                    metrics["loss"].append(loss)
                    metrics["accuracy"].append(accuracy)
                    
                    # Update job metrics
                    job.metrics = {
                        "current_step": step + 1,
                        "total_steps": steps,
                        "loss": loss,
                        "accuracy": accuracy,
                        "progress": (step + 1) / steps
                    }
                    await db.commit()
                    
                    # Simulate training time
                    await asyncio.sleep(2)
                    
                # Create output model
                output_model_name = job.output_model_name or f"{base_model.name}-ft-{job_id}"
                
                # Create model file (just a placeholder in this implementation)
                model_file = os.path.join(job_dir, "model.bin")
                async with aiofiles.open(model_file, "w") as f:
                    await f.write(f"Fine-tuned model: {output_model_name}")
                    
                # Create model card
                model_card = {
                    "name": output_model_name,
                    "base_model": base_model.name,
                    "fine_tuning_job_id": job_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "metrics": {
                        "final_loss": metrics["loss"][-1],
                        "final_accuracy": metrics["accuracy"][-1]
                    },
                    "hyperparameters": job.hyperparameters
                }
                
                model_card_file = os.path.join(job_dir, "model_card.json")
                async with aiofiles.open(model_card_file, "w") as f:
                    await f.write(json.dumps(model_card, indent=2))
                    
                # Add model to database
                new_model = LLMModel(
                    name=output_model_name,
                    version="1.0",
                    description=f"Fine-tuned from {base_model.name}",
                    parameters=base_model.parameters,
                    quantization=base_model.quantization,
                    is_fine_tuned=True,
                    base_model=base_model.name
                )
                
                db.add(new_model)
                await db.commit()
                await db.refresh(new_model)
                
                # Update job
                job.status = FineTuningJobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.output_model_name = output_model_name
                job.metrics = {
                    **job.metrics,
                    "final_loss": metrics["loss"][-1],
                    "final_accuracy": metrics["accuracy"][-1],
                    "model_id": new_model.id
                }
                
                logger.info(f"Fine-tuning job {job_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error in fine-tuning job {job_id}: {str(e)}")
                
                # Update job status to failed
                job.status = FineTuningJobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.metrics = {
                    **(job.metrics or {}),
                    "error": str(e)
                }
                
            finally:
                # Remove from active jobs
                if job_id in self.active_jobs:
                    del self.active_jobs[job_id]
                    
                # Commit final job status
                await db.commit()
                
    async def create_job(
        self,
        name: str,
        base_model_id: int,
        user_id: int,
        training_file: str,
        validation_file: Optional[str] = None,
        description: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        output_model_name: Optional[str] = None
    ) -> int:
        """Create a new fine-tuning job"""
        async with get_db() as db:
            from sqlalchemy import select
            
            # Check if base model exists
            stmt = select(LLMModel).where(LLMModel.id == base_model_id)
            result = await db.execute(stmt)
            base_model = result.scalars().first()
            
            if not base_model:
                raise ValueError(f"Base model with ID {base_model_id} not found")
                
            # Check if user exists
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
                
            # Create job
            job = FineTuningJob(
                name=name,
                user_id=user_id,
                base_model_id=base_model_id,
                status=FineTuningJobStatus.QUEUED,
                description=description,
                training_file=training_file,
                validation_file=validation_file,
                hyperparameters=hyperparameters,
                output_model_name=output_model_name
            )
            
            db.add(job)
            await db.commit()
            await db.refresh(job)
            
            logger.info(f"Created fine-tuning job {job.id}")
            return job.id
            
    async def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job details"""
        async with get_db() as db:
            from sqlalchemy import select
            
            # Get job
            stmt = select(FineTuningJob).where(FineTuningJob.id == job_id)
            result = await db.execute(stmt)
            job = result.scalars().first()
            
            if not job:
                return None
                
            # Get base model
            stmt = select(LLMModel).where(LLMModel.id == job.base_model_id)
            result = await db.execute(stmt)
            base_model = result.scalars().first()
            
            return {
                "id": job.id,
                "name": job.name,
                "status": job.status.value,
                "user_id": job.user_id,
                "base_model": {
                    "id": base_model.id if base_model else None,
                    "name": base_model.name if base_model else None
                },
                "description": job.description,
                "training_file": job.training_file,
                "validation_file": job.validation_file,
                "hyperparameters": job.hyperparameters,
                "metrics": job.metrics,
                "output_model_name": job.output_model_name,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "is_active": job.id in self.active_jobs
            }
            
    async def cancel_job(self, job_id: int) -> bool:
        """Cancel a fine-tuning job"""
        async with get_db() as db:
            from sqlalchemy import select
            
            # Get job
            stmt = select(FineTuningJob).where(FineTuningJob.id == job_id)
            result = await db.execute(stmt)
            job = result.scalars().first()
            
            if not job:
                return False
                
            # Can only cancel queued, preparing, or running jobs
            if job.status not in [
                FineTuningJobStatus.QUEUED,
                FineTuningJobStatus.PREPARING,
                FineTuningJobStatus.RUNNING
            ]:
                return False
                
            # Update job status
            job.status = FineTuningJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            
            # Remove from active jobs if present
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
                
            await db.commit()
            logger.info(f"Cancelled fine-tuning job {job_id}")
            return True
            
    async def list_jobs(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List fine-tuning jobs"""
        async with get_db() as db:
            from sqlalchemy import select
            
            # Build query
            query = select(FineTuningJob)
            
            if user_id is not None:
                query = query.where(FineTuningJob.user_id == user_id)
                
            if status is not None:
                query = query.where(FineTuningJob.status == getattr(FineTuningJobStatus, status.upper(), None))
                
            # Add pagination
            query = query.order_by(FineTuningJob.created_at.desc()).offset(offset).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            jobs = result.scalars().all()
            
            # Get base models for all jobs
            model_ids = [job.base_model_id for job in jobs]
            if model_ids:
                stmt = select(LLMModel).where(LLMModel.id.in_(model_ids))
                result = await db.execute(stmt)
                models = {model.id: model for model in result.scalars().all()}
            else:
                models = {}
                
            # Format results
            return [
                {
                    "id": job.id,
                    "name": job.name,
                    "status": job.status.value,
                    "base_model": {
                        "id": job.base_model_id,
                        "name": models[job.base_model_id].name if job.base_model_id in models else None
                    },
                    "output_model_name": job.output_model_name,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "progress": job.metrics.get("progress", 0) if job.metrics else 0,
                    "is_active": job.id in self.active_jobs
                }
                for job in jobs
            ]
