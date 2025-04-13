import enum
import datetime
import uuid
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from database import Base

def generate_uuid():
    """Generate a unique ID for records"""
    return str(uuid.uuid4())

class UserRole(enum.Enum):
    """User role enum for role-based permissions"""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    USER = "user"

class User(Base, UserMixin):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True)
    email = Column(String(64), unique=True, index=True)
    full_name = Column(String(64))
    password_hash = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="user")
    
    def get_id(self):
        """Return the user ID as a string"""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """Return True if the user is authenticated"""
        return True
    
    @property
    def is_anonymous(self):
        """Return False as anonymous users are not supported"""
        return False

class ApiKey(Base):
    """API key model for authenticating API requests"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, index=True, default=generate_uuid)
    name = Column(String(64))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class LLMModel(Base):
    """LLM model information"""
    __tablename__ = "llm_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True)
    version = Column(String(32))
    description = Column(Text)
    parameters = Column(BigInteger, default=0)  # Model size in parameters
    quantization = Column(String(16), nullable=True)  # Quantization method (e.g., int8, int4)
    is_fine_tuned = Column(Boolean, default=False)
    base_model = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    queries = relationship("Query", back_populates="model")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="base_model", foreign_keys="FineTuningJob.base_model_id")
    
class ServerNode(Base):
    """GPU Server node information"""
    __tablename__ = "server_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True)
    host = Column(String(128))
    port = Column(Integer, default=8080)
    api_key = Column(String(256), nullable=True)
    gpu_count = Column(Integer, default=1)
    gpu_memory = Column(Integer, default=24)  # GB of VRAM
    is_active = Column(Boolean, default=True)
    health_status = Column(String(16), default="unknown")
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    load_metrics = relationship("ServerLoadMetrics", back_populates="server", cascade="all, delete-orphan")
    
class ServerLoadMetrics(Base):
    """Server load metrics for load balancing"""
    __tablename__ = "server_load_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("server_nodes.id", ondelete="CASCADE"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    gpu_utilization = Column(Float, default=0.0)  # Percentage (0-100)
    gpu_memory_used = Column(Float, default=0.0)  # GB
    gpu_memory_total = Column(Float, default=0.0)  # GB
    cpu_utilization = Column(Float, default=0.0)  # Percentage (0-100)
    active_requests = Column(Integer, default=0)
    queue_depth = Column(Integer, default=0)
    
    # Relationships
    server = relationship("ServerNode", back_populates="load_metrics")

class QueryStatus(enum.Enum):
    """Query status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"

class QuerySource(enum.Enum):
    """Source of the query"""
    WEB_UI = "web_ui"
    API = "api"
    FOCAL_BI = "focal_bi"
    CLI = "cli"
    SYSTEM = "system"

class Query(Base):
    """Query log for tracking all LLM requests"""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    model_id = Column(Integer, ForeignKey("llm_models.id"))
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    status = Column(Enum(QueryStatus), default=QueryStatus.PENDING)
    source = Column(Enum(QuerySource), default=QuerySource.WEB_UI)
    token_count_prompt = Column(Integer, default=0)
    token_count_response = Column(Integer, default=0)
    processing_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    client_ip = Column(String(64), nullable=True)
    cached = Column(Boolean, default=False)
    cache_key = Column(String(64), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    query_metadata = Column(JSON, nullable=True)  # Additional query metadata
    
    # Relationships
    user = relationship("User", back_populates="queries")
    model = relationship("LLMModel", back_populates="queries")

class SemanticCacheEntry(Base):
    """Semantic cache entries for optimizing repeated queries"""
    __tablename__ = "semantic_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Text, nullable=True)  # Store as serialized vector
    response_text = Column(Text, nullable=False)
    model_id = Column(Integer, ForeignKey("llm_models.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    hit_count = Column(Integer, default=0)
    
class FineTuningJobStatus(enum.Enum):
    """Fine-tuning job status enum"""
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FineTuningJob(Base):
    """Fine-tuning job information"""
    __tablename__ = "fine_tuning_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    base_model_id = Column(Integer, ForeignKey("llm_models.id"))
    status = Column(Enum(FineTuningJobStatus), default=FineTuningJobStatus.QUEUED)
    description = Column(Text, nullable=True)
    training_file = Column(String(256), nullable=True)
    validation_file = Column(String(256), nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)  # Training metrics
    output_model_name = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="fine_tuning_jobs")
    base_model = relationship("LLMModel", foreign_keys=[base_model_id], back_populates="fine_tuning_jobs")

class OpenAPISpec(Base):
    """OpenAPI specification for extending capabilities"""
    __tablename__ = "openapi_specs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True)
    description = Column(Text, nullable=True)
    spec_json = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemBackup(Base):
    """System backup information"""
    __tablename__ = "system_backups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), index=True)
    description = Column(Text, nullable=True)
    backup_path = Column(String(256), nullable=False)
    size_bytes = Column(BigInteger, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    backup_type = Column(String(32), default="full")  # full, models, database, config
    status = Column(String(16), default="completed")
