#!/bin/bash
# Deployment configuration for Enterprise LLM Platform

# This script configures deployment for self-hosted environments
# The script edits the deployment target to use the correct command

echo "Setting up deployment configuration..."

# For production, use the main.py Flask application with gunicorn
# as it has proven to work reliably with database connections
cat > deployment-commands.txt << EOL
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers 4 main:app"]
EOL

echo "The application is configured to use gunicorn with main:app (Flask)"
echo "This avoids the sslmode error that occurs with uvicorn and FastAPI"
echo "Use this configuration for your deployment"

# Configure environment variables for production deployment
cat > deployment-env-example.txt << EOL
# Required environment variables for deployment
# Copy these to your deployment environment variables section

# Application settings
ENVIRONMENT=production
DEBUG=false
SESSION_SECRET=your_secure_random_secret_key_here

# Database settings - Option 1: Use DATABASE_URL 
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Database settings - Option 2: Use individual PostgreSQL credentials
# These will be used to construct the DATABASE_URL if it's not provided
# PGHOST=your_postgres_host
# PGPORT=your_postgres_port
# PGUSER=your_postgres_user
# PGPASSWORD=your_postgres_password
# PGDATABASE=your_postgres_database

# LLM configuration settings
# LLM_DEFAULT_MODEL=mistral-7b
# LLM_ENDPOINT_URL=http://your-llm-server:8080/api/generate
# LLM_API_KEY=your_llm_api_key
# ENABLE_LOAD_BALANCING=true
# LOAD_BALANCER_STRATEGY=round_robin
# ENABLE_SEMANTIC_CACHE=true

# Optional integration settings
# FOCAL_BI_ENDPOINT=http://your-focal-bi-server/api
# FOCAL_BI_API_KEY=your_focal_bi_api_key
# TABBY_ML_ENDPOINT=http://your-tabby-ml-server/api
EOL

echo "Created deployment-env-example.txt with required environment variables"
echo "Make sure to set these environment variables in your deployment settings"

# Set basic environment variables for production
echo "ENVIRONMENT=production" > .env.production
echo "DEBUG=false" >> .env.production

echo "Deployment configuration complete"
echo "Remember to use the Flask application (main:app) with gunicorn, not the FastAPI application (app:app) with uvicorn"