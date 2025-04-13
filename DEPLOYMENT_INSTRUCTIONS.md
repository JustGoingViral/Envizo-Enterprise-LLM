# Deployment Instructions for Enterprise LLM Platform

## Issue Found
The deployment is failing because the `.deployment-config` file's deployment configuration is still using FastAPI with uvicorn instead of Flask with gunicorn. This causes database connection issues with the `sslmode` parameter.

## How to Fix

### Step 1: Update the Deployment Command
1. Go to your your deployment environment project dashboard
2. Click on the "Tools" menu at the top
3. Select "Deployment" from the dropdown
4. In the deployment settings, find the "Run Command" field
5. Replace the current command with:
   ```
   gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
   ```
6. Save the changes

### Step 2: Environment Variables
Make sure your deployment has the following environment variables set:

1. **Required Variables**:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
   - `SESSION_SECRET=your_secure_random_secret_here`

2. **Database Configuration** (Option 1 - Recommended):
   - `DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require`
   
   **Database Configuration** (Option 2):
   - `PGHOST=your_postgres_host`
   - `PGPORT=your_postgres_port` (typically 5432)
   - `PGUSER=your_postgres_user`
   - `PGPASSWORD=your_postgres_password`
   - `PGDATABASE=your_postgres_database`

### Step 3: Disable Automatic Package Installation
To prevent package installation issues during deployment:
1. In the deployment settings
2. Uncheck "Install packages from requirements.txt or other package files automatically" if present
3. This ensures all necessary packages are specified in your project configuration

## Why This Fix Works
1. Using gunicorn with Flask (main:app) avoids the sslmode parameter issue
2. The sslmode parameter is properly handled in the database connection string as a query parameter
3. The deployment environment runs in production mode with appropriate settings

## Critical Database Connection Issue Explained

The root cause of the deployment failure is how PostgreSQL SSL connections are handled with asyncpg:

### ❌ What Causes the Error
When using asyncpg (required for FastAPI's async support), the `sslmode` parameter has to be specified in the connection URL, not as a keyword argument.

If your code has:
```python
# This will FAIL with asyncpg
async_engine = create_async_engine(
    "postgresql+asyncpg://user:password@host:port/database", 
    connect_args={"sslmode": "require"}
)
```

### ✅ The Correct Solution
There are two valid approaches to handle SSL with asyncpg:

**Approach 1: SSL in URL (Our Current Implementation)**  
Include sslmode as part of the URL as a query parameter:
```python
# This is CORRECT
async_engine = create_async_engine(
    "postgresql+asyncpg://user:password@host:port/database?sslmode=require",
    echo=False,
    future=True  # Optional: Enables SQLAlchemy 2.0 behavior
)
```

**Approach 2: SSL Context (Alternative)**  
Use an SSL context object with connect_args:
```python
import ssl

ssl_context = ssl.create_default_context()
# You can configure the ssl_context as needed
async_engine = create_async_engine(
    "postgresql+asyncpg://user:password@host:port/database",
    connect_args={"ssl": ssl_context},
    echo=False,
    future=True
)
```

**IMPORTANT: Never mix both approaches!** Using `?sslmode=require` in the URL while also passing `connect_args={"sslmode": "require"}` will cause errors.

**Note on conflicting information:** Some sources claim that asyncpg only accepts `?ssl=require` (not `?sslmode=require`) in the URL. Our testing confirms that with recent versions of asyncpg, **both parameters work correctly**. The critical issue is avoiding parameter duplication between the URL and connect_args.

This issue only affects async connections with asyncpg, which is why the Flask (non-async) version works correctly.

## Troubleshooting
If deployment still fails:
1. Check the deployment logs for specific error messages
2. Verify that the database connection string is correctly formatted with `?sslmode=require`
3. Ensure your Postgres database is accessible from the deployment environment

## Local Testing
Run the following command locally to test the production configuration:
```bash
ENVIRONMENT=production DEBUG=false gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

For more detailed deployment information, refer to the README.md file.