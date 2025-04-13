import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from config import settings

logger = logging.getLogger(__name__)

# Define Base class for models
class Base(DeclarativeBase):
    pass

# Database setup - Synchronous
sync_engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Database setup - Asynchronous 
# Convert postgres:// to postgresql:// for async dialect
async_url = settings.DATABASE_URL

# Handle sslmode as a query parameter, not a keyword argument
# This fixes the "TypeError: connect() got an unexpected keyword argument 'sslmode'" error
if 'postgresql' in async_url and 'sslmode=' not in async_url:
    # Add sslmode as a query parameter if it's not already there
    if '?' in async_url:
        # URL already has query parameters, add sslmode as an additional parameter
        async_url += "&sslmode=require" 
    else:
        # URL has no query parameters, add sslmode as the first parameter
        async_url += "?sslmode=require"
    logger.info("Added sslmode=require as query parameter to database URL")

# Update dialect for asyncpg
if async_url.startswith('postgres://'):
    async_url = async_url.replace('postgres://', 'postgresql+asyncpg://', 1)
elif not async_url.startswith('postgresql+asyncpg://'):
    async_url = async_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

# Create async engine and session
try:
    # Explicitly create the engine without any connect_args
    # This is crucial for asyncpg as sslmode must be in the URL, not connect_args
    async_engine = create_async_engine(
        async_url,
        echo=False,
        future=True  # Enables SQLAlchemy 2.0 behavior
    )
    AsyncSessionLocal = sessionmaker(
        class_=AsyncSession, 
        expire_on_commit=False,
        autocommit=False, 
        autoflush=False, 
        bind=async_engine
    )
    logger.info("Async database engine configured successfully")
except Exception as e:
    logger.error(f"Failed to configure async database engine: {str(e)}")
    AsyncSessionLocal = None

# PostgreSQL analytics database setup
if all([settings.PGHOST, settings.PGUSER, settings.PGDATABASE]):
    try:
        # Include sslmode as a query parameter, not as a keyword argument
        pg_url = f"postgresql://{settings.PGUSER}:{settings.PGPASSWORD}@{settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE}?sslmode=require"
        pg_engine = create_engine(pg_url)
        PGSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
        logger.info("PostgreSQL analytics database configured")
    except Exception as e:
        logger.error(f"Failed to configure PostgreSQL connection: {str(e)}")
        PGSessionLocal = None
else:
    PGSessionLocal = None
    logger.warning("PostgreSQL analytics database not configured")

def init_db():
    """Initialize the database"""
    try:
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

async def init_async_db():
    """Initialize the database using async engine"""
    try:
        # Create all tables if they don't exist
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully (async)")
    except Exception as e:
        logger.error(f"Async database initialization error: {str(e)}")
        raise

# Synchronous session functions
def get_db():
    """Get a database session - generator style for FastAPI dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def get_db_session():
    """Get a database session - direct return style for Flask"""
    try:
        db = SessionLocal()
        return db
    except Exception as e:
        logger.error(f"Error creating database session: {str(e)}")
        raise

# Asynchronous session functions
async def get_async_db():
    """Get an async database session for FastAPI dependency injection"""
    if AsyncSessionLocal is None:
        raise Exception("Async database not configured")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

class AsyncDBSession:
    """Async context manager for database sessions"""
    def __init__(self):
        if AsyncSessionLocal is None:
            raise Exception("Async database not configured")
        self.session = None
        
    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        return await self.session.__aenter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
            
def get_async_db_ctx():
    """Get an async database session as a context manager for use with async with"""
    return AsyncDBSession()

def get_pg_db():
    """Get a PostgreSQL database session for analytics"""
    if PGSessionLocal is None:
        return None
    
    db = None
    try:
        db = PGSessionLocal()
        return db
    except Exception as e:
        logger.error(f"Error creating PostgreSQL session: {str(e)}")
        if db:
            db.close()
        return None
