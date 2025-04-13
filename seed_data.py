
import os
import random
import logging
import datetime
from typing import List, Dict, Any
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from database import get_db_session
from models import (
    User, UserRole, ApiKey, LLMModel, Query, QueryStatus, QuerySource,
    ServerNode, ServerLoadMetrics, FineTuningJob, FineTuningJobStatus,
    SemanticCacheEntry, OpenAPISpec, SystemBackup
)

logger = logging.getLogger(__name__)

# Sample data for various entities
SAMPLE_USER_NAMES = [
    "admin", "john.doe", "jane.smith", "alex.johnson", "sam.wilson",
    "taylor.brown", "jordan.chen", "casey.miller", "morgan.patel", "riley.wong"
]

SAMPLE_MODEL_NAMES = [
    "mistral-7b", "llama-3-8b", "gemma-7b", "mistral-7b-instruct", 
    "llama-3-70b", "phi-2", "finetuned-mistral-legal", "finetuned-llama-finance"
]

SAMPLE_SERVER_NAMES = [
    "gpu-server-a100-1", "gpu-server-a100-2", "gpu-server-h100-1", 
    "gpu-server-rtx-1", "gpu-server-rtx-2", "gpu-server-rtx-3"
]

SAMPLE_QUERIES = [
    "Explain quantum computing in simple terms",
    "What are the main differences between SQL and NoSQL databases?",
    "How can we implement a secure authentication system?",
    "Create a marketing strategy for a new AI product",
    "Write a function to reverse a linked list in Python",
    "Summarize the key points of the last quarterly earnings report",
    "What regulations should we consider for our AI deployment?",
    "How does a transformer architecture work?",
    "What's the best way to optimize database queries?",
    "Draft a privacy policy for our enterprise AI application"
]

def seed_all_data():
    """Seed all data for testing purposes"""
    try:
        db = get_db_session()
        logger.info("Starting data seeding process...")
        
        # Seed in order to maintain referential integrity
        seed_users(db)
        seed_models(db)
        seed_servers(db)
        seed_server_metrics(db)
        seed_queries(db)
        seed_fine_tuning_jobs(db)
        seed_api_keys(db)
        seed_openapi_specs(db)
        seed_system_backups(db)
        seed_semantic_cache(db)
        
        logger.info("Data seeding completed successfully")
        return {
            "status": "success",
            "message": "Successfully seeded all data for testing"
        }
    except Exception as e:
        logger.error(f"Error seeding data: {str(e)}")
        return {
            "status": "error",
            "message": f"Error seeding data: {str(e)}"
        }
    finally:
        if db:
            db.close()

def seed_users(db):
    """Seed user data"""
    logger.info("Seeding users...")
    
    # Check if users already exist
    if db.query(User).count() > 3:
        logger.info("Users already seeded, skipping")
        return
    
    # Create users with different roles
    roles = list(UserRole)
    
    for i, username in enumerate(SAMPLE_USER_NAMES):
        # Skip if already exists
        if db.query(User).filter(User.username == username).first():
            continue
            
        role = roles[i % len(roles)]
        user = User(
            username=username,
            email=f"{username}@example.com",
            full_name=f"{username.replace('.', ' ').title()}",
            password_hash=generate_password_hash("password123"),
            role=role
        )
        db.add(user)
    
    db.commit()
    logger.info(f"Seeded {len(SAMPLE_USER_NAMES)} users")

def seed_models(db):
    """Seed LLM model data"""
    logger.info("Seeding LLM models...")
    
    # Check if models already exist
    if db.query(LLMModel).count() > 3:
        logger.info("Models already seeded, skipping")
        return
    
    # Sample model details
    for i, name in enumerate(SAMPLE_MODEL_NAMES):
        # Skip if already exists
        if db.query(LLMModel).filter(LLMModel.name == name).first():
            continue
            
        # Set is_fine_tuned based on name
        is_fine_tuned = "finetuned" in name
        
        # Calculate parameters based on model name
        if "70b" in name:
            parameters = 70000000000
        elif "7b" in name:
            parameters = 7000000000
        elif "3-8b" in name:
            parameters = 8000000000
        else:
            parameters = 2000000000
        
        # Set quantization
        if i % 3 == 0:
            quantization = "int8"
        elif i % 3 == 1:
            quantization = "int4"
        else:
            quantization = None
            
        model = LLMModel(
            name=name,
            version="1.0",
            description=f"{name.title()} language model",
            parameters=parameters,
            quantization=quantization,
            is_fine_tuned=is_fine_tuned,
            base_model=name.split("-")[0] if is_fine_tuned else None
        )
        db.add(model)
    
    db.commit()
    logger.info(f"Seeded {len(SAMPLE_MODEL_NAMES)} LLM models")

def seed_servers(db):
    """Seed server node data"""
    logger.info("Seeding server nodes...")
    
    # Check if servers already exist
    if db.query(ServerNode).count() > 2:
        logger.info("Server nodes already seeded, skipping")
        return
    
    # Sample server details
    for i, name in enumerate(SAMPLE_SERVER_NAMES):
        # Skip if already exists
        if db.query(ServerNode).filter(ServerNode.name == name).first():
            continue
            
        # Set GPU count and memory based on server type
        if "a100" in name:
            gpu_count = 8
            gpu_memory = 80
        elif "h100" in name:
            gpu_count = 4
            gpu_memory = 96
        else:  # RTX
            gpu_count = 4
            gpu_memory = 24
            
        # Set health status
        if i % 5 == 0:
            health_status = "degraded"
        elif i % 10 == 0:
            health_status = "offline"
        else:
            health_status = "healthy"
            
        server = ServerNode(
            name=name,
            host=f"192.168.1.{10 + i}",
            port=8080,
            api_key=f"server_api_key_{i}" if i % 2 == 0 else None,
            gpu_count=gpu_count,
            gpu_memory=gpu_memory,
            is_active=True,
            health_status=health_status,
            last_health_check=datetime.datetime.utcnow() - datetime.timedelta(minutes=random.randint(1, 60))
        )
        db.add(server)
    
    db.commit()
    logger.info(f"Seeded {len(SAMPLE_SERVER_NAMES)} server nodes")

def seed_server_metrics(db):
    """Seed server load metrics data"""
    logger.info("Seeding server load metrics...")
    
    # Get all servers
    servers = db.query(ServerNode).all()
    
    # Check if metrics already exist
    existing_count = db.query(ServerLoadMetrics).count()
    if existing_count > len(servers) * 10:
        logger.info("Server metrics already seeded, skipping")
        return
    
    # Generate metrics for the past 24 hours
    now = datetime.datetime.utcnow()
    time_points = []
    
    # Generate 24 time points for the past 24 hours
    for i in range(24):
        time_points.append(now - datetime.timedelta(hours=i))
    
    # Add metrics for each server at each time point
    for server in servers:
        for time_point in time_points:
            # Base values that increase/decrease over time to create trends
            base_gpu_util = 30 + random.randint(-10, 60)
            base_memory_used = server.gpu_memory * (base_gpu_util / 100)
            
            metric = ServerLoadMetrics(
                server_id=server.id,
                timestamp=time_point,
                gpu_utilization=max(0, min(100, base_gpu_util)),
                gpu_memory_used=max(0, min(server.gpu_memory, base_memory_used)),
                gpu_memory_total=server.gpu_memory,
                cpu_utilization=random.uniform(10, 90),
                active_requests=random.randint(0, 20),
                queue_depth=random.randint(0, 5)
            )
            db.add(metric)
    
    db.commit()
    logger.info(f"Seeded {len(servers) * len(time_points)} server load metrics")

def seed_queries(db):
    """Seed query data"""
    logger.info("Seeding queries...")
    
    # Check if queries already exist
    if db.query(Query).count() > 50:
        logger.info("Queries already seeded, skipping")
        return
    
    # Get users and models
    users = db.query(User).all()
    models = db.query(LLMModel).all()
    
    if not users or not models:
        logger.warning("No users or models found, skipping query seeding")
        return
    
    # Create queries over the past 7 days
    now = datetime.datetime.utcnow()
    
    # Generate 200 sample queries
    for i in range(200):
        # Random creation time within the past 7 days
        created_at = now - datetime.timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Random user (sometimes null for anonymous)
        user = random.choice(users) if random.random() > 0.1 else None
        
        # Random model
        model = random.choice(models)
        
        # Random query text
        query_text = random.choice(SAMPLE_QUERIES)
        
        # Random query source
        source = random.choice(list(QuerySource))
        
        # Query status (mostly completed, some failed)
        status = QueryStatus.FAILED if random.random() < 0.05 else QueryStatus.COMPLETED
        
        # Create query
        query = Query(
            user_id=user.id if user else None,
            model_id=model.id,
            query_text=query_text,
            response_text="Sample response for " + query_text if status == QueryStatus.COMPLETED else None,
            status=status,
            source=source,
            token_count_prompt=random.randint(10, 100),
            token_count_response=random.randint(50, 500) if status == QueryStatus.COMPLETED else 0,
            processing_time_ms=random.uniform(100, 5000) if status == QueryStatus.COMPLETED else 0,
            created_at=created_at,
            completed_at=created_at + datetime.timedelta(seconds=random.uniform(0.5, 10)) if status == QueryStatus.COMPLETED else None,
            client_ip=f"192.168.1.{random.randint(2, 254)}",
            cached=random.random() < 0.2,
            cache_key=f"cache_key_{i}" if random.random() < 0.2 else None,
            error_message="Sample error message" if status == QueryStatus.FAILED else None,
            query_metadata={"source_app": f"app_{random.randint(1, 5)}"} if random.random() < 0.5 else None
        )
        db.add(query)
    
    db.commit()
    logger.info("Seeded 200 queries")

def seed_fine_tuning_jobs(db):
    """Seed fine-tuning job data"""
    logger.info("Seeding fine-tuning jobs...")
    
    # Check if jobs already exist
    if db.query(FineTuningJob).count() > 5:
        logger.info("Fine-tuning jobs already seeded, skipping")
        return
    
    # Get users and models
    users = db.query(User).all()
    models = db.query(LLMModel).filter(LLMModel.is_fine_tuned == False).all()
    
    if not users or not models:
        logger.warning("No users or models found, skipping fine-tuning job seeding")
        return
    
    # Create directory for fine-tuning files if it doesn't exist
    fine_tuning_dir = os.path.join("data", "fine_tuning")
    os.makedirs(fine_tuning_dir, exist_ok=True)
    
    # Sample job statuses
    statuses = list(FineTuningJobStatus)
    
    # Create 10 sample jobs
    for i in range(10):
        # Random creation time within the past 30 days
        now = datetime.datetime.utcnow()
        created_at = now - datetime.timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Random user
        user = random.choice(users)
        
        # Random model
        model = random.choice(models)
        
        # Random status
        status = random.choice(statuses)
        
        # Start and completion times based on status
        started_at = None
        completed_at = None
        
        if status in [FineTuningJobStatus.RUNNING, FineTuningJobStatus.COMPLETED, FineTuningJobStatus.FAILED]:
            started_at = created_at + datetime.timedelta(hours=random.uniform(0.5, 2))
            
        if status in [FineTuningJobStatus.COMPLETED, FineTuningJobStatus.FAILED]:
            completed_at = started_at + datetime.timedelta(hours=random.uniform(2, 10))
        
        # Training file
        training_file = os.path.join(fine_tuning_dir, f"training_data_{i}.jsonl")
        
        # Create empty training file
        with open(training_file, "w") as f:
            f.write('{"prompt": "Sample prompt", "completion": "Sample completion"}\n')
        
        # Validation file (sometimes null)
        validation_file = None
        if random.random() > 0.5:
            validation_file = os.path.join(fine_tuning_dir, f"validation_data_{i}.jsonl")
            with open(validation_file, "w") as f:
                f.write('{"prompt": "Sample validation prompt", "completion": "Sample validation completion"}\n')
        
        # Hyperparameters
        hyperparameters = {
            "learning_rate": random.choice([1e-5, 2e-5, 3e-5]),
            "epochs": random.randint(1, 5),
            "batch_size": random.choice([8, 16, 32]),
            "warmup_steps": random.choice([100, 200, 500]),
            "weight_decay": 0.01,
            "lora_rank": random.choice([8, 16, 32]),
            "lora_alpha": 32,
            "lora_dropout": 0.05
        }
        
        # Metrics (if completed)
        metrics = None
        if status == FineTuningJobStatus.COMPLETED:
            metrics = {
                "train_loss": random.uniform(0.5, 2.0),
                "validation_loss": random.uniform(0.5, 2.5),
                "final_learning_rate": hyperparameters["learning_rate"],
                "tokens_processed": random.randint(10000, 1000000),
                "training_duration_seconds": random.randint(3600, 36000)
            }
        
        # Output model name
        output_model_name = f"finetuned-{model.name}-{i}" if status == FineTuningJobStatus.COMPLETED else None
        
        # Create job
        job = FineTuningJob(
            name=f"Finetune-{model.name}-Job-{i}",
            user_id=user.id,
            base_model_id=model.id,
            status=status,
            description=f"Fine-tuning job for {model.name}",
            training_file=training_file,
            validation_file=validation_file,
            hyperparameters=hyperparameters,
            metrics=metrics,
            output_model_name=output_model_name,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at
        )
        db.add(job)
    
    db.commit()
    logger.info("Seeded 10 fine-tuning jobs")

def seed_api_keys(db):
    """Seed API keys"""
    logger.info("Seeding API keys...")
    
    # Check if API keys already exist
    if db.query(ApiKey).count() > 5:
        logger.info("API keys already seeded, skipping")
        return
    
    # Get users
    users = db.query(User).all()
    
    if not users:
        logger.warning("No users found, skipping API key seeding")
        return
    
    # Create API keys
    for i, user in enumerate(users):
        # Create 1-3 keys per user
        num_keys = random.randint(1, 3)
        
        for j in range(num_keys):
            # Skip if more than 3 keys already exist for this user
            if db.query(ApiKey).filter(ApiKey.user_id == user.id).count() >= 3:
                continue
                
            # Random expiry (some never expire, some expired, some active)
            expires_at = None
            if random.random() < 0.7:  # 70% have expiry
                if random.random() < 0.2:  # 20% of those are expired
                    expires_at = datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 30))
                else:  # 80% expire in the future
                    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=random.randint(30, 365))
            
            # Create API key
            key = ApiKey(
                key=f"sk-api{i}-{j}-{random.randint(1000, 9999)}-{random.randint(10000, 99999)}",
                name=f"API Key {j+1} for {user.username}",
                user_id=user.id,
                is_active=random.random() < 0.9,  # 90% active
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 90)),
                expires_at=expires_at
            )
            db.add(key)
    
    db.commit()
    logger.info("Seeded API keys for users")

def seed_openapi_specs(db):
    """Seed OpenAPI specifications"""
    logger.info("Seeding OpenAPI specs...")
    
    # Check if specs already exist
    if db.query(OpenAPISpec).count() > 0:
        logger.info("OpenAPI specs already seeded, skipping")
        return
    
    # Sample OpenAPI specs
    specs = [
        {
            "name": "weather-api",
            "description": "Weather information API",
            "spec_json": {
                "openapi": "3.0.0",
                "info": {
                    "title": "Weather API",
                    "version": "1.0.0"
                },
                "paths": {
                    "/weather": {
                        "get": {
                            "summary": "Get weather information",
                            "parameters": [
                                {
                                    "name": "location",
                                    "in": "query",
                                    "required": True,
                                    "schema": {"type": "string"}
                                }
                            ]
                        }
                    }
                }
            }
        },
        {
            "name": "crm-api",
            "description": "Customer Relationship Management API",
            "spec_json": {
                "openapi": "3.0.0",
                "info": {
                    "title": "CRM API",
                    "version": "1.0.0"
                },
                "paths": {
                    "/customers": {
                        "get": {
                            "summary": "Get customer information"
                        }
                    }
                }
            }
        },
        {
            "name": "stock-api",
            "description": "Stock market data API",
            "spec_json": {
                "openapi": "3.0.0",
                "info": {
                    "title": "Stock API",
                    "version": "1.0.0"
                },
                "paths": {
                    "/stock/{symbol}": {
                        "get": {
                            "summary": "Get stock information",
                            "parameters": [
                                {
                                    "name": "symbol",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"}
                                }
                            ]
                        }
                    }
                }
            }
        }
    ]
    
    # Create specs
    for spec_data in specs:
        spec = OpenAPISpec(
            name=spec_data["name"],
            description=spec_data["description"],
            spec_json=spec_data["spec_json"],
            is_active=True,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 30))
        )
        db.add(spec)
    
    db.commit()
    logger.info(f"Seeded {len(specs)} OpenAPI specs")

def seed_system_backups(db):
    """Seed system backup records"""
    logger.info("Seeding system backups...")
    
    # Check if backups already exist
    if db.query(SystemBackup).count() > 0:
        logger.info("System backups already seeded, skipping")
        return
    
    # Get admin users
    admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
    
    if not admins:
        logger.warning("No admin users found, skipping system backup seeding")
        return
    
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join("data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Sample backup types
    backup_types = ["full", "database", "models", "config"]
    
    # Generate 10 backups over the past 60 days
    now = datetime.datetime.utcnow()
    
    for i in range(10):
        # Random creation time within the past 60 days
        created_at = now - datetime.timedelta(
            days=random.randint(0, 60),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Format date for backup path
        date_str = created_at.strftime("%Y%m%d_%H%M%S")
        
        # Random backup type
        backup_type = random.choice(backup_types)
        
        # Random admin
        admin = random.choice(admins)
        
        # Create backup path
        backup_path = os.path.join(backup_dir, f"{date_str}_{backup_type}")
        os.makedirs(backup_path, exist_ok=True)
        
        # Create a dummy file in the backup directory
        with open(os.path.join(backup_path, "backup_info.json"), "w") as f:
            f.write('{"backup_type": "' + backup_type + '", "created_at": "' + date_str + '"}')
        
        # Random size based on backup type
        if backup_type == "full":
            size_bytes = random.randint(100000000, 500000000)  # 100MB-500MB
        elif backup_type == "database":
            size_bytes = random.randint(10000000, 50000000)  # 10MB-50MB
        elif backup_type == "models":
            size_bytes = random.randint(50000000, 200000000)  # 50MB-200MB
        else:  # config
            size_bytes = random.randint(100000, 1000000)  # 100KB-1MB
        
        # Create backup record
        backup = SystemBackup(
            name=f"{backup_type.title()} Backup {date_str}",
            description=f"Scheduled {backup_type} backup",
            backup_path=backup_path,
            size_bytes=size_bytes,
            created_at=created_at,
            created_by_id=admin.id,
            backup_type=backup_type,
            status="completed"
        )
        db.add(backup)
    
    db.commit()
    logger.info("Seeded 10 system backups")

def seed_semantic_cache(db):
    """Seed semantic cache entries"""
    logger.info("Seeding semantic cache entries...")
    
    # Check if cache entries already exist
    if db.query(SemanticCacheEntry).count() > 10:
        logger.info("Semantic cache entries already seeded, skipping")
        return
    
    # Get models
    models = db.query(LLMModel).all()
    
    if not models:
        logger.warning("No models found, skipping semantic cache seeding")
        return
    
    # Sample queries
    queries = [
        "What is machine learning?",
        "Explain the transformer architecture",
        "What's the difference between SQL and NoSQL?",
        "How does BERT work?",
        "What are the best practices for API security?",
        "Explain the concept of data normalization",
        "What is the CAP theorem?",
        "How do I implement a JWT authentication system?",
        "What is the time complexity of quicksort?",
        "Explain the concept of containerization",
        "What are microservices?",
        "How does Kubernetes work?",
        "What is the observer pattern?",
        "Explain the concept of database indexing",
        "What is the SOLID principle in OOP?"
    ]
    
    # Generate embeddings (dummy for now)
    def generate_dummy_embedding():
        return ",".join([str(random.uniform(-1, 1)) for _ in range(10)])
    
    # Generate 30 cache entries
    now = datetime.datetime.utcnow()
    
    for i in range(30):
        # Random creation time within the past 7 days
        created_at = now - datetime.timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Random expiry (1-30 days from creation)
        expires_at = created_at + datetime.timedelta(days=random.randint(1, 30))
        
        # Random model
        model = random.choice(models)
        
        # Random query
        query_text = random.choice(queries)
        
        # Create cache entry
        entry = SemanticCacheEntry(
            query_text=query_text,
            query_embedding=generate_dummy_embedding(),
            response_text=f"Cached response for: {query_text}",
            model_id=model.id,
            created_at=created_at,
            expires_at=expires_at,
            hit_count=random.randint(1, 50)
        )
        db.add(entry)
    
    db.commit()
    logger.info("Seeded 30 semantic cache entries")

if __name__ == "__main__":
    # This allows running the seeder directly
    result = seed_all_data()
    print(result["message"])
