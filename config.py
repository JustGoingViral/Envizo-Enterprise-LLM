import os
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Simple settings class
class Settings:
    # Application settings
    APP_NAME: str = "Envizo AI Platform"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    # Cast to str to satisfy type checker, empty string will be replaced with a random key
    SECRET_KEY: str = str(os.environ.get("SESSION_SECRET", ""))
    if not SECRET_KEY and ENVIRONMENT != "test":
        # In production and development, a secret key is required
        # Generate a secure random key if not provided
        import secrets
        logger.warning("No SESSION_SECRET environment variable found, generating a random one.")
        logger.warning("This is NOT recommended for production. Set SESSION_SECRET in your environment.")
        SECRET_KEY = secrets.token_hex(32)
    
    # Database settings
    # Initialize as None and assign a concrete string value later
    DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        # Try to construct PostgreSQL URL from individual parameters
        if all([os.getenv("PGHOST"), os.getenv("PGUSER"), os.getenv("PGDATABASE")]):
            pguser = os.getenv("PGUSER", "")
            pgpassword = os.getenv("PGPASSWORD", "")
            pghost = os.getenv("PGHOST", "")
            pgport = os.getenv("PGPORT", "5432")
            pgdatabase = os.getenv("PGDATABASE", "")
            # Include sslmode as a query parameter, not as a keyword argument
            DATABASE_URL = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}?sslmode=require"
            logger.info("Constructed DATABASE_URL from individual PostgreSQL parameters")
        else:
            logger.warning("No DATABASE_URL environment variable found, using SQLite database.")
            logger.warning("This is NOT recommended for production. Set DATABASE_URL in your environment.")
            DATABASE_URL = "sqlite:///./enterprise_llm.db"
    
    # PostgreSQL settings for analytics
    PGHOST: Optional[str] = os.getenv("PGHOST")
    PGUSER: Optional[str] = os.getenv("PGUSER")
    PGDATABASE: Optional[str] = os.getenv("PGDATABASE")
    PGPORT: Optional[str] = os.getenv("PGPORT")
    PGPASSWORD: Optional[str] = os.getenv("PGPASSWORD")
    
    # Authentication settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # LLM Server settings
    LLM_DEFAULT_MODEL: str = os.getenv("LLM_DEFAULT_MODEL", "mistral-7b")
    LLM_ENDPOINT_URL: str = os.getenv("LLM_ENDPOINT_URL", "http://localhost:8080/api/generate")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    LLM_REQUEST_TIMEOUT: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "30"))
    
    # Load balancer settings
    ENABLE_LOAD_BALANCING: bool = os.getenv("ENABLE_LOAD_BALANCING", "True").lower() == "true"
    LOAD_BALANCER_STRATEGY: str = os.getenv("LOAD_BALANCER_STRATEGY", "round_robin")  # round_robin, least_load, gpu_memory
    
    # Semantic cache settings
    ENABLE_SEMANTIC_CACHE: bool = os.getenv("ENABLE_SEMANTIC_CACHE", "True").lower() == "true"
    SEMANTIC_CACHE_EXPIRY_SECONDS: int = int(os.getenv("SEMANTIC_CACHE_EXPIRY_SECONDS", "3600"))
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_SIMILARITY_THRESHOLD", "0.95"))
    
    # Fine-tuning settings
    FINE_TUNING_OUTPUT_DIR: str = os.getenv("FINE_TUNING_OUTPUT_DIR", "./fine_tuned_models")
    
    # TabbyML integration
    TABBY_ML_ENDPOINT: Optional[str] = os.getenv("TABBY_ML_ENDPOINT")
    
    # Business Intelligence integration
    BI_ENDPOINT: Optional[str] = os.getenv("BI_ENDPOINT")
    BI_API_KEY: Optional[str] = os.getenv("BI_API_KEY")
    
    def __init__(self):
        # Parse LLM servers 
        self.LLM_SERVERS = self._parse_llm_servers()
    
    def _parse_llm_servers(self) -> List[Dict[str, Any]]:
        """Parse LLM servers from environment variables or use defaults"""
        # Load from environment if available
        servers_str = os.getenv("LLM_SERVERS")
        if servers_str:
            try:
                return json.loads(servers_str)
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM_SERVERS environment variable")
        
        # Default configuration with a single server
        return [
            {
                "name": "default-gpu-server",
                "url": self.LLM_ENDPOINT_URL,
                "api_key": self.LLM_API_KEY,
                "gpu_memory": 24,  # GB of VRAM
                "models": [self.LLM_DEFAULT_MODEL]
            }
        ]


# Create settings instance
settings = Settings()

# Log configuration details (excluding sensitive information)
logger.info(f"Application: {settings.APP_NAME}")
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"Debug mode: {settings.DEBUG}")
logger.info(f"Database URL: {settings.DATABASE_URL}")
logger.info(f"LLM load balancing enabled: {settings.ENABLE_LOAD_BALANCING}")
logger.info(f"LLM load balancing strategy: {settings.LOAD_BALANCER_STRATEGY}")
logger.info(f"Semantic cache enabled: {settings.ENABLE_SEMANTIC_CACHE}")
logger.info(f"Number of LLM servers configured: {len(settings.LLM_SERVERS)}")
