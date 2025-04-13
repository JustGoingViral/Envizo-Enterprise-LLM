from pydantic import BaseModel, Field, validator, EmailStr, AnyHttpUrl
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import enum

# User schemas
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    USER = "user"

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.USER

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class User(UserInDB):
    pass

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    exp: int
    role: UserRole

class LoginRequest(BaseModel):
    username: str
    password: str

# API Key schemas
class ApiKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None

class ApiKey(BaseModel):
    id: int
    key: str
    name: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# LLM schemas
class LLMPromptRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class LLMResponse(BaseModel):
    response: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    processing_time_ms: float
    created_at: datetime
    query_id: int
    cached: bool = False

class LLMModelInfo(BaseModel):
    id: int
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[int] = None
    quantization: Optional[str] = None
    is_fine_tuned: bool = False
    base_model: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Server node schemas
class ServerNodeCreate(BaseModel):
    name: str
    host: str
    port: int = 8080
    api_key: Optional[str] = None
    gpu_count: int = 1
    gpu_memory: int = 24
    is_active: bool = True

class ServerNodeUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    api_key: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_memory: Optional[int] = None
    is_active: Optional[bool] = None
    health_status: Optional[str] = None

class ServerNode(BaseModel):
    id: int
    name: str
    host: str
    port: int
    gpu_count: int
    gpu_memory: int
    is_active: bool
    health_status: str
    last_health_check: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ServerLoadMetrics(BaseModel):
    server_id: int
    gpu_utilization: float
    gpu_memory_used: float
    gpu_memory_total: float
    cpu_utilization: float
    active_requests: int
    queue_depth: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Query schemas
class QueryStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"

class QuerySource(str, enum.Enum):
    WEB_UI = "web_ui"
    API = "api"
    FOCAL_BI = "focal_bi"
    CLI = "cli"
    SYSTEM = "system"

class QueryRecord(BaseModel):
    id: int
    user_id: Optional[int] = None
    query_text: str
    response_text: Optional[str] = None
    status: QueryStatus
    source: QuerySource
    token_count_prompt: int
    token_count_response: int
    processing_time_ms: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    cached: bool = False
    model: Optional[LLMModelInfo] = None

    class Config:
        from_attributes = True

class QueryStats(BaseModel):
    total_queries: int
    avg_processing_time_ms: float
    total_tokens_processed: int
    cache_hit_ratio: float
    queries_per_model: Dict[str, int]

# Fine-tuning schemas
class FineTuningJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FineTuningJobCreate(BaseModel):
    name: str
    base_model_id: int
    description: Optional[str] = None
    training_file: str
    validation_file: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    output_model_name: Optional[str] = None

class FineTuningJob(BaseModel):
    id: int
    name: str
    user_id: int
    base_model_id: int
    status: FineTuningJobStatus
    description: Optional[str] = None
    training_file: str
    validation_file: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    output_model_name: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# OpenAPI schemas
class OpenAPISpecCreate(BaseModel):
    name: str
    description: Optional[str] = None
    spec_json: Dict[str, Any]

class OpenAPISpec(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    spec_json: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Analytics schemas
class TimeRange(BaseModel):
    start_date: datetime
    end_date: datetime

class QueryAnalytics(BaseModel):
    total_queries: int
    queries_per_day: Dict[str, int]
    avg_processing_time_ms: float
    token_usage: Dict[str, int]
    popular_models: List[Dict[str, Any]]
    cache_hit_ratio: float

class SystemMetrics(BaseModel):
    cpu_utilization: float
    memory_utilization: float
    disk_usage: float
    gpu_utilization: List[Dict[str, Any]]
    active_users: int
    uptime_days: float

# System backup schemas
class SystemBackupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    backup_type: str = "full"

class SystemBackup(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    backup_path: str
    size_bytes: int
    created_at: datetime
    created_by_id: Optional[int] = None
    backup_type: str
    status: str

    class Config:
        from_attributes = True

# Focal BI integration schemas
class FocalBIIntegrationRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    report_id: Optional[str] = None
    user_id: Optional[str] = None
    dashboard_id: Optional[str] = None

class FocalBIIntegrationResponse(BaseModel):
    result: str
    query_id: int
    suggestions: Optional[List[str]] = None
    sql: Optional[str] = None
    execution_time_ms: float
