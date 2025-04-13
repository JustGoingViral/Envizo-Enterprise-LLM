import logging
import httpx
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User
from utils import get_current_user, verify_api_key
from schemas import FocalBIIntegrationRequest, FocalBIIntegrationResponse
from llm.inference import LLMInferenceManager

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create inference manager
inference_manager = LLMInferenceManager()

@router.on_event("startup")
async def startup_event():
    await inference_manager.initialize()

@router.post("/query", response_model=FocalBIIntegrationResponse)
async def focal_bi_query(
    request: FocalBIIntegrationRequest,
    api_key: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Integration endpoint for Focal BI queries
    """
    try:
        # Check for API key
        if not api_key:
            # Try header
            api_key = request.headers.get("X-API-Key")
            
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key required"
            )
            
        # Verify API key
        user = await verify_api_key(api_key, db)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
            
        # Process query using LLM
        result = await inference_manager.generate(
            prompt=f"FOCAL BI QUERY: {request.query}\nCONTEXT: {request.context if request.context else 'No context provided'}",
            model_name=settings.LLM_DEFAULT_MODEL,
            user_id=user.id,
            source="focal_bi",
            metadata={
                "report_id": request.report_id,
                "dashboard_id": request.dashboard_id,
                "focal_bi_user_id": request.user_id
            },
            db=db
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to generate response")
            )
            
        # If TabbyML integration is configured, try to generate SQL
        sql = None
        if settings.TABBY_ML_ENDPOINT:
            try:
                # Prepare TabbyML request
                tabby_request = {
                    "prompt": f"Generate SQL for: {request.query}",
                    "context": request.context
                }
                
                # Send request to TabbyML
                async with httpx.AsyncClient(timeout=5.0) as client:
                    tabby_response = await client.post(
                        f"{settings.TABBY_ML_ENDPOINT}/api/generate",
                        json=tabby_request,
                        headers={"Authorization": f"Bearer {settings.TABBY_ML_API_KEY}" if settings.TABBY_ML_API_KEY else None}
                    )
                    
                if tabby_response.status_code == 200:
                    tabby_result = tabby_response.json()
                    sql = tabby_result.get("sql") or tabby_result.get("response")
            except Exception as e:
                logger.warning(f"Error generating SQL with TabbyML: {str(e)}")
                # Continue without SQL, it's optional
                
        # Generate suggestions based on the query
        suggestions = [
            f"Show me {request.query} over time",
            f"Compare {request.query} by department",
            f"What factors affect {request.query}?"
        ]
        
        # Return response
        return FocalBIIntegrationResponse(
            result=result["response"],
            query_id=result["query_id"],
            suggestions=suggestions,
            sql=sql,
            execution_time_ms=result["processing_time_ms"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Focal BI query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@router.post("/analyze-dashboard")
async def analyze_dashboard(
    dashboard_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a Focal BI dashboard and provide insights
    """
    try:
        # Extract dashboard info
        dashboard_id = dashboard_data.get("dashboard_id")
        dashboard_name = dashboard_data.get("name", "Unnamed Dashboard")
        charts = dashboard_data.get("charts", [])
        metrics = dashboard_data.get("metrics", [])
        
        if not dashboard_id:
            raise HTTPException(
                status_code=400,
                detail="dashboard_id is required"
            )
            
        # Prepare prompt for the LLM
        chart_descriptions = "\n".join([f"- {chart.get('title', 'Untitled Chart')}: {chart.get('description', 'No description')}" for chart in charts])
        metric_descriptions = "\n".join([f"- {metric.get('name', 'Unnamed Metric')}: {metric.get('value', 'N/A')}" for metric in metrics])
        
        prompt = f"""
        Analyze the following Focal BI dashboard and provide insights:
        
        Dashboard: {dashboard_name}
        Dashboard ID: {dashboard_id}
        
        Charts:
        {chart_descriptions}
        
        Metrics:
        {metric_descriptions}
        
        Provide a summary of the dashboard's main purpose and key insights that can be derived from it.
        """
        
        # Generate analysis using LLM
        result = await inference_manager.generate(
            prompt=prompt,
            model_name=settings.LLM_DEFAULT_MODEL,
            user_id=current_user.id,
            source="focal_bi",
            metadata={
                "dashboard_id": dashboard_id,
                "dashboard_name": dashboard_name
            },
            db=db
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to analyze dashboard")
            )
            
        # Return analysis
        return {
            "dashboard_id": dashboard_id,
            "analysis": result["response"],
            "query_id": result["query_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing dashboard: {str(e)}"
        )

@router.get("/connection-status")
async def get_connection_status(
    current_user: User = Depends(get_current_user)
):
    """
    Check connection status with Focal BI
    """
    try:
        # Check if Focal BI integration is configured
        if not settings.FOCAL_BI_ENDPOINT:
            return {
                "connected": False,
                "status": "Focal BI endpoint not configured",
                "endpoint": None
            }
            
        # Try to connect to Focal BI
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.FOCAL_BI_ENDPOINT}/api/health",
                    headers={"Authorization": f"Bearer {settings.FOCAL_BI_API_KEY}" if settings.FOCAL_BI_API_KEY else None}
                )
                
            if response.status_code == 200:
                return {
                    "connected": True,
                    "status": "Connected",
                    "endpoint": settings.FOCAL_BI_ENDPOINT,
                    "version": response.json().get("version", "Unknown")
                }
            else:
                return {
                    "connected": False,
                    "status": f"Connection failed: HTTP {response.status_code}",
                    "endpoint": settings.FOCAL_BI_ENDPOINT
                }
                
        except Exception as e:
            return {
                "connected": False,
                "status": f"Connection error: {str(e)}",
                "endpoint": settings.FOCAL_BI_ENDPOINT
            }
            
    except Exception as e:
        logger.error(f"Error checking Focal BI connection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking connection: {str(e)}"
        )

@router.post("/generate-report-insights")
async def generate_report_insights(
    report_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate insights for a Focal BI report
    """
    try:
        # Extract report info
        report_id = report_data.get("report_id")
        report_name = report_data.get("name", "Unnamed Report")
        data_points = report_data.get("data_points", [])
        time_range = report_data.get("time_range", {})
        
        if not report_id:
            raise HTTPException(
                status_code=400,
                detail="report_id is required"
            )
            
        # Prepare sample data points for the prompt
        sample_data = "\n".join([f"- {point}" for point in data_points[:5]])
        if len(data_points) > 5:
            sample_data += f"\n- ... and {len(data_points) - 5} more data points"
            
        time_range_text = f"{time_range.get('start', 'unknown')} to {time_range.get('end', 'unknown')}"
        
        prompt = f"""
        Generate insights for the following Focal BI report:
        
        Report: {report_name}
        Report ID: {report_id}
        Time Range: {time_range_text}
        
        Sample Data:
        {sample_data}
        
        Provide a comprehensive analysis of the data, including trends, anomalies, and actionable insights.
        Focus on business impact and recommendations.
        """
        
        # Generate insights using LLM
        result = await inference_manager.generate(
            prompt=prompt,
            model_name=settings.LLM_DEFAULT_MODEL,
            user_id=current_user.id,
            source="focal_bi",
            metadata={
                "report_id": report_id,
                "report_name": report_name
            },
            db=db
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to generate insights")
            )
            
        # Return insights
        return {
            "report_id": report_id,
            "insights": result["response"],
            "query_id": result["query_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating insights: {str(e)}"
        )
