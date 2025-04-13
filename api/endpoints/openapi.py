import logging
import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, OpenAPISpec
from utils import get_current_user
from auth.permissions import PermissionManager
from schemas import OpenAPISpecCreate, OpenAPISpec as OpenAPISpecSchema

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create permission manager
permission_manager = PermissionManager()

@router.post("/specs", response_model=OpenAPISpecSchema)
async def create_openapi_spec(
    spec_data: OpenAPISpecCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new OpenAPI specification
    """
    try:
        # Check if user has permission to manage models
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_MODEL_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to manage OpenAPI specs"
            )
            
        # Validate spec JSON
        try:
            json.dumps(spec_data.spec_json)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid JSON in spec_json: {str(e)}"
            )
            
        # Check if name already exists
        from sqlalchemy import select
        
        stmt = select(OpenAPISpec).where(OpenAPISpec.name == spec_data.name)
        result = await db.execute(stmt)
        existing_spec = result.scalars().first()
        
        if existing_spec:
            raise HTTPException(
                status_code=409,
                detail=f"OpenAPI spec with name '{spec_data.name}' already exists"
            )
            
        # Create new spec
        new_spec = OpenAPISpec(
            name=spec_data.name,
            description=spec_data.description,
            spec_json=spec_data.spec_json,
            is_active=True
        )
        
        db.add(new_spec)
        await db.commit()
        await db.refresh(new_spec)
        
        return OpenAPISpecSchema(
            id=new_spec.id,
            name=new_spec.name,
            description=new_spec.description,
            spec_json=new_spec.spec_json,
            is_active=new_spec.is_active,
            created_at=new_spec.created_at,
            updated_at=new_spec.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating OpenAPI spec: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating OpenAPI spec: {str(e)}"
        )

@router.post("/upload")
async def upload_openapi_spec(
    file: UploadFile = File(...),
    name: str = Body(...),
    description: Optional[str] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an OpenAPI specification file
    """
    try:
        # Check if user has permission to manage models
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_MODEL_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to manage OpenAPI specs"
            )
            
        # Check file extension
        allowed_extensions = [".json", ".yaml", ".yml"]
        file_ext = file.filename.split(".")[-1].lower()
        
        if f".{file_ext}" not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
            
        # Read file content
        content = await file.read()
        
        # Parse JSON content
        try:
            if file_ext == "json":
                spec_json = json.loads(content.decode())
            else:
                # For YAML format, would need yaml parser like PyYAML
                # For this implementation, we'll assume JSON only
                raise HTTPException(
                    status_code=400,
                    detail="Only JSON format is currently supported"
                )
                
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid JSON format: {str(e)}"
            )
            
        # Check if name already exists
        from sqlalchemy import select
        
        stmt = select(OpenAPISpec).where(OpenAPISpec.name == name)
        result = await db.execute(stmt)
        existing_spec = result.scalars().first()
        
        if existing_spec:
            raise HTTPException(
                status_code=409,
                detail=f"OpenAPI spec with name '{name}' already exists"
            )
            
        # Create new spec
        new_spec = OpenAPISpec(
            name=name,
            description=description,
            spec_json=spec_json,
            is_active=True
        )
        
        db.add(new_spec)
        await db.commit()
        await db.refresh(new_spec)
        
        return {
            "id": new_spec.id,
            "name": new_spec.name,
            "description": new_spec.description,
            "is_active": new_spec.is_active,
            "created_at": new_spec.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading OpenAPI spec: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading OpenAPI spec: {str(e)}"
        )

@router.get("/specs", response_model=List[OpenAPISpecSchema])
async def list_openapi_specs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all OpenAPI specifications
    """
    try:
        # Check if user has permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_API_ACCESS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view OpenAPI specs"
            )
            
        # Get all specs
        from sqlalchemy import select
        
        stmt = select(OpenAPISpec).order_by(OpenAPISpec.name)
        result = await db.execute(stmt)
        specs = result.scalars().all()
        
        # Convert to schema
        return [
            OpenAPISpecSchema(
                id=spec.id,
                name=spec.name,
                description=spec.description,
                spec_json=spec.spec_json,
                is_active=spec.is_active,
                created_at=spec.created_at,
                updated_at=spec.updated_at
            )
            for spec in specs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing OpenAPI specs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing OpenAPI specs: {str(e)}"
        )

@router.get("/specs/{spec_id}", response_model=OpenAPISpecSchema)
async def get_openapi_spec(
    spec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get an OpenAPI specification by ID
    """
    try:
        # Check if user has permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_API_ACCESS):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view OpenAPI specs"
            )
            
        # Get spec
        from sqlalchemy import select
        
        stmt = select(OpenAPISpec).where(OpenAPISpec.id == spec_id)
        result = await db.execute(stmt)
        spec = result.scalars().first()
        
        if not spec:
            raise HTTPException(
                status_code=404,
                detail=f"OpenAPI spec with ID {spec_id} not found"
            )
            
        return OpenAPISpecSchema(
            id=spec.id,
            name=spec.name,
            description=spec.description,
            spec_json=spec.spec_json,
            is_active=spec.is_active,
            created_at=spec.created_at,
            updated_at=spec.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting OpenAPI spec: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting OpenAPI spec: {str(e)}"
        )

@router.put("/specs/{spec_id}")
async def update_openapi_spec(
    spec_id: int,
    spec_update: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an OpenAPI specification
    """
    try:
        # Check if user has permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_MODEL_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to manage OpenAPI specs"
            )
            
        # Get spec
        from sqlalchemy import select
        
        stmt = select(OpenAPISpec).where(OpenAPISpec.id == spec_id)
        result = await db.execute(stmt)
        spec = result.scalars().first()
        
        if not spec:
            raise HTTPException(
                status_code=404,
                detail=f"OpenAPI spec with ID {spec_id} not found"
            )
            
        # Update fields
        if "name" in spec_update:
            # Check if name already exists for a different spec
            stmt = select(OpenAPISpec).where(
                OpenAPISpec.name == spec_update["name"],
                OpenAPISpec.id != spec_id
            )
            result = await db.execute(stmt)
            existing_spec = result.scalars().first()
            
            if existing_spec:
                raise HTTPException(
                    status_code=409,
                    detail=f"OpenAPI spec with name '{spec_update['name']}' already exists"
                )
                
            spec.name = spec_update["name"]
            
        if "description" in spec_update:
            spec.description = spec_update["description"]
            
        if "spec_json" in spec_update:
            # Validate spec JSON
            try:
                json.dumps(spec_update["spec_json"])
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid JSON in spec_json: {str(e)}"
                )
                
            spec.spec_json = spec_update["spec_json"]
            
        if "is_active" in spec_update:
            spec.is_active = spec_update["is_active"]
            
        # Update spec
        await db.commit()
        await db.refresh(spec)
        
        return {
            "id": spec.id,
            "name": spec.name,
            "description": spec.description,
            "is_active": spec.is_active,
            "created_at": spec.created_at.isoformat(),
            "updated_at": spec.updated_at.isoformat() if spec.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OpenAPI spec: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating OpenAPI spec: {str(e)}"
        )

@router.delete("/specs/{spec_id}")
async def delete_openapi_spec(
    spec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an OpenAPI specification
    """
    try:
        # Check if user has permission
        if not permission_manager.has_permission(current_user, permission_manager.PERMISSION_MODEL_MANAGEMENT):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to manage OpenAPI specs"
            )
            
        # Get spec
        from sqlalchemy import select, delete
        
        stmt = select(OpenAPISpec).where(OpenAPISpec.id == spec_id)
        result = await db.execute(stmt)
        spec = result.scalars().first()
        
        if not spec:
            raise HTTPException(
                status_code=404,
                detail=f"OpenAPI spec with ID {spec_id} not found"
            )
            
        # Delete spec
        stmt = delete(OpenAPISpec).where(OpenAPISpec.id == spec_id)
        await db.execute(stmt)
        await db.commit()
        
        return {"message": "OpenAPI spec deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting OpenAPI spec: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting OpenAPI spec: {str(e)}"
        )
