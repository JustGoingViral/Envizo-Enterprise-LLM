import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from database import get_db
from models import User, QueryStatus, UserRole
from utils import get_current_user
from auth.permissions import PermissionManager
from schemas import TimeRange, QueryAnalytics, SystemMetrics

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create permission manager
permission_manager = PermissionManager()

@router.get("/query-stats")
async def get_query_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    model_id: Optional[int] = None,
    source: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get query statistics for the given time range
    """
    try:
        # Check if user has analytics permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_ANALYTICS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view analytics"
            )
            
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
            
        # Get query statistics
        from sqlalchemy import func, select, and_
        from models import Query, LLMModel, QueryStatus, QuerySource
        
        # Build base query
        query = select(
            Query.id,
            Query.status,
            Query.source,
            Query.model_id,
            Query.token_count_prompt,
            Query.token_count_response,
            Query.processing_time_ms,
            Query.cached,
            Query.created_at,
            LLMModel.name.label("model_name")
        ).join(
            LLMModel,
            Query.model_id == LLMModel.id
        ).where(
            and_(
                Query.created_at >= start_date,
                Query.created_at <= end_date
            )
        )
        
        # Add filters if provided
        if model_id:
            query = query.where(Query.model_id == model_id)
        if source:
            query = query.where(Query.source == getattr(QuerySource, source.upper(), None))
            
        # Execute query
        result = await db.execute(query)
        queries = result.all()
        
        # Calculate statistics
        total_queries = len(queries)
        completed_queries = len([q for q in queries if q.status == QueryStatus.COMPLETED])
        cached_queries = len([q for q in queries if q.cached])
        failed_queries = len([q for q in queries if q.status == QueryStatus.FAILED])
        
        total_processing_time = sum([q.processing_time_ms for q in queries if q.processing_time_ms])
        avg_processing_time = total_processing_time / completed_queries if completed_queries else 0
        
        total_prompt_tokens = sum([q.token_count_prompt for q in queries if q.token_count_prompt])
        total_response_tokens = sum([q.token_count_response for q in queries if q.token_count_response])
        total_tokens = total_prompt_tokens + total_response_tokens
        
        cache_hit_ratio = cached_queries / total_queries if total_queries else 0
        
        # Group by model
        queries_by_model = {}
        for q in queries:
            model_name = q.model_name
            if model_name not in queries_by_model:
                queries_by_model[model_name] = 0
            queries_by_model[model_name] += 1
            
        # Group by source
        queries_by_source = {}
        for q in queries:
            source = q.source.value
            if source not in queries_by_source:
                queries_by_source[source] = 0
            queries_by_source[source] += 1
            
        # Group by day
        queries_by_day = {}
        for q in queries:
            day = q.created_at.date().isoformat()
            if day not in queries_by_day:
                queries_by_day[day] = 0
            queries_by_day[day] += 1
            
        return {
            "total_queries": total_queries,
            "completed_queries": completed_queries,
            "cached_queries": cached_queries,
            "failed_queries": failed_queries,
            "avg_processing_time_ms": avg_processing_time,
            "total_prompt_tokens": total_prompt_tokens,
            "total_response_tokens": total_response_tokens,
            "total_tokens": total_tokens,
            "cache_hit_ratio": cache_hit_ratio,
            "queries_by_model": queries_by_model,
            "queries_by_source": queries_by_source,
            "queries_by_day": queries_by_day,
            "time_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting query statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting query statistics: {str(e)}"
        )

@router.get("/user-stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user statistics
    """
    try:
        # Check if user has analytics permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_ANALYTICS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view analytics"
            )
            
        # Get user statistics
        from sqlalchemy import func, select
        from models import User, UserRole
        
        # Total users
        stmt = select(func.count()).select_from(User)
        result = await db.execute(stmt)
        total_users = result.scalar()
        
        # Active users
        stmt = select(func.count()).select_from(User).where(User.is_active == True)
        result = await db.execute(stmt)
        active_users = result.scalar()
        
        # Users by role
        users_by_role = {}
        for role in UserRole:
            stmt = select(func.count()).select_from(User).where(User.role == role)
            result = await db.execute(stmt)
            users_by_role[role.value] = result.scalar()
            
        # New users in the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stmt = select(func.count()).select_from(User).where(User.created_at >= thirty_days_ago)
        result = await db.execute(stmt)
        new_users_30d = result.scalar()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "users_by_role": users_by_role,
            "new_users_30d": new_users_30d
        }
        
    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting user statistics: {str(e)}"
        )

@router.get("/system-metrics", response_model=SystemMetrics)
async def get_system_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system metrics
    """
    try:
        # Check if user has analytics permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_ANALYTICS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view analytics"
            )
            
        # Get system metrics from servers
        from models import ServerNode, ServerLoadMetrics
        from sqlalchemy import select, desc
        
        # Get active servers
        stmt = select(ServerNode).where(ServerNode.is_active == True)
        result = await db.execute(stmt)
        servers = result.scalars().all()
        
        # Get latest load metrics for each server
        gpu_utilization = []
        total_cpu_utilization = 0
        total_active_users = 0
        
        for server in servers:
            stmt = select(ServerLoadMetrics).where(
                ServerLoadMetrics.server_id == server.id
            ).order_by(
                desc(ServerLoadMetrics.timestamp)
            ).limit(1)
            
            result = await db.execute(stmt)
            metrics = result.scalars().first()
            
            if metrics:
                gpu_utilization.append({
                    "server_name": server.name,
                    "utilization": metrics.gpu_utilization,
                    "memory_used": metrics.gpu_memory_used,
                    "memory_total": metrics.gpu_memory_total,
                    "active_requests": metrics.active_requests
                })
                
                total_cpu_utilization += metrics.cpu_utilization
                total_active_users += metrics.active_requests
                
        # Calculate averages
        avg_cpu_utilization = total_cpu_utilization / len(servers) if servers else 0
        
        # Count active user sessions
        from sqlalchemy import func
        from models import Query
        
        # Active users in the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stmt = select(
            func.count(func.distinct(Query.user_id))
        ).where(
            Query.created_at >= one_hour_ago
        )
        
        result = await db.execute(stmt)
        active_users_last_hour = result.scalar() or 0
        
        # Uptime calculation (dummy value for now)
        uptime_days = 30.0
        
        # Disk usage (dummy values for now)
        disk_usage = 70.0
        
        return SystemMetrics(
            cpu_utilization=avg_cpu_utilization,
            memory_utilization=80.0,  # Dummy value
            disk_usage=disk_usage,
            gpu_utilization=gpu_utilization,
            active_users=active_users_last_hour,
            uptime_days=uptime_days
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting system metrics: {str(e)}"
        )

@router.get("/model-performance")
async def get_model_performance(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for each model
    """
    try:
        # Check if user has analytics permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_ANALYTICS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view analytics"
            )
            
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
            
        # Get model performance metrics
        from sqlalchemy import func, select, and_
        from models import Query, LLMModel
        
        # Get all models
        stmt = select(LLMModel)
        result = await db.execute(stmt)
        models = result.scalars().all()
        
        performance_metrics = []
        
        for model in models:
            # Get completed queries for this model
            stmt = select(
                func.count().label("total_queries"),
                func.avg(Query.processing_time_ms).label("avg_processing_time"),
                func.sum(Query.token_count_prompt).label("total_prompt_tokens"),
                func.sum(Query.token_count_response).label("total_response_tokens"),
                func.sum(Query.token_count_prompt + Query.token_count_response).label("total_tokens")
            ).where(
                and_(
                    Query.model_id == model.id,
                    Query.status == QueryStatus.COMPLETED,
                    Query.created_at >= start_date,
                    Query.created_at <= end_date
                )
            )
            
            result = await db.execute(stmt)
            metrics = result.first()
            
            # Get cached queries
            stmt = select(
                func.count()
            ).where(
                and_(
                    Query.model_id == model.id,
                    Query.cached == True,
                    Query.created_at >= start_date,
                    Query.created_at <= end_date
                )
            )
            
            result = await db.execute(stmt)
            cached_queries = result.scalar() or 0
            
            # Get failed queries
            stmt = select(
                func.count()
            ).where(
                and_(
                    Query.model_id == model.id,
                    Query.status == QueryStatus.FAILED,
                    Query.created_at >= start_date,
                    Query.created_at <= end_date
                )
            )
            
            result = await db.execute(stmt)
            failed_queries = result.scalar() or 0
            
            total_queries = metrics.total_queries or 0
            cache_hit_ratio = cached_queries / total_queries if total_queries > 0 else 0
            
            performance_metrics.append({
                "model_id": model.id,
                "model_name": model.name,
                "is_fine_tuned": model.is_fine_tuned,
                "total_queries": total_queries,
                "cached_queries": cached_queries,
                "failed_queries": failed_queries,
                "avg_processing_time_ms": metrics.avg_processing_time or 0,
                "total_prompt_tokens": metrics.total_prompt_tokens or 0,
                "total_response_tokens": metrics.total_response_tokens or 0,
                "total_tokens": metrics.total_tokens or 0,
                "cache_hit_ratio": cache_hit_ratio,
                "success_rate": (total_queries - failed_queries) / total_queries if total_queries > 0 else 0
            })
            
        return {
            "model_performance": performance_metrics,
            "time_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting model performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting model performance: {str(e)}"
        )

@router.get("/recent-queries")
async def get_recent_queries(
    limit: int = 100,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent queries
    """
    try:
        # If user is not admin and requesting another user's queries, restrict access
        if (user_id and user_id != current_user.id and 
            not permission_manager.has_permission(current_user, permission_manager.PERMISSION_ANALYTICS)):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view other users' queries"
            )
            
        # Set user_id filter to current user if not provided and user is not admin
        if not user_id and not permission_manager.has_permission(current_user, permission_manager.PERMISSION_ANALYTICS):
            user_id = current_user.id
            
        # Get recent queries
        from sqlalchemy import select, desc
        from models import Query, LLMModel, User
        
        # Build query
        query = select(
            Query.id,
            Query.query_text,
            Query.response_text,
            Query.status,
            Query.source,
            Query.token_count_prompt,
            Query.token_count_response,
            Query.processing_time_ms,
            Query.created_at,
            Query.completed_at,
            Query.cached,
            Query.error_message,
            LLMModel.name.label("model_name"),
            User.username.label("username")
        ).join(
            LLMModel,
            Query.model_id == LLMModel.id
        ).outerjoin(
            User,
            Query.user_id == User.id
        )
        
        # Add user filter if provided
        if user_id:
            query = query.where(Query.user_id == user_id)
            
        # Order by created_at desc and limit
        query = query.order_by(desc(Query.created_at)).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        queries = result.all()
        
        # Format results
        return {
            "queries": [
                {
                    "id": q.id,
                    "query_text": q.query_text,
                    "response_text": q.response_text,
                    "status": q.status.value,
                    "source": q.source.value,
                    "token_count_prompt": q.token_count_prompt,
                    "token_count_response": q.token_count_response,
                    "processing_time_ms": q.processing_time_ms,
                    "created_at": q.created_at.isoformat(),
                    "completed_at": q.completed_at.isoformat() if q.completed_at else None,
                    "cached": q.cached,
                    "error_message": q.error_message,
                    "model_name": q.model_name,
                    "username": q.username
                }
                for q in queries
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent queries: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting recent queries: {str(e)}"
        )
