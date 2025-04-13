#!/bin/bash
# Deployment script for Enterprise LLM Platform

# This script prepares the application for deployment by:
# 1. Setting up the correct deployment configuration
# 2. Creating necessary deployment files
# 3. Providing guidance on environment variables

echo "=== Enterprise LLM Platform Deployment ==="
echo "Preparing application for deployment..."

# Run the deployment configuration script
./deployment-config.sh

# Check if the script created the deployment command file
if [ -f "deployment-commands.txt" ]; then
    echo "Deployment command configuration successful"
    
    # Copy the deployment commands to .deployment-config file
    if [ -f ".deployment-config" ]; then
        # Backup the existing .deployment-config file
        cp .deployment-config .deployment-config.backup
        echo "Backed up existing .deployment-config file to .deployment-config.backup"
        
        # Check if the .deployment-config file already has a [deployment] section
        if grep -q "\[deployment\]" .deployment-config; then
            # Remove the existing [deployment] section
            sed -i '/\[deployment\]/,/^$/d' .deployment-config
        fi
        
        # Append the deployment configuration
        cat deployment-commands.txt >> .deployment-config
        echo "Updated .deployment-config file with deployment configuration"
    else
        echo "No .deployment-config file found, creating a new one"
        cp deployment-commands.txt .deployment-config
    fi
else
    echo "Error: deployment-commands.txt not found. Deployment configuration failed."
    exit 1
fi

# Check if deployment-env-example.txt exists
if [ -f "deployment-env-example.txt" ]; then
    echo ""
    echo "=== Environment Variables Required for Deployment ==="
    cat deployment-env-example.txt
    echo ""
    echo "Make sure to add these environment variables in your your deployment environment Deployment settings."
else
    echo "Warning: deployment-env-example.txt not found. Check deployment-config.sh script."
fi

echo ""
echo "=== Database Configuration ==="
echo "The application is configured to use PostgreSQL with proper sslmode handling."
echo "Make sure your DATABASE_URL includes ?sslmode=require or set individual PG* variables."
echo ""

echo "=== Web Server Configuration ==="
echo "The application is configured to use Flask with gunicorn for deployment."
echo "This avoids the sslmode error that occurs with FastAPI and uvicorn."
echo ""

echo "=== Deployment Instructions ==="
echo "1. Commit all changes to your repository"
echo "2. Configure the required environment variables in your deployment environment Deployment settings"
echo "3. Click the 'Deploy' button in the your deployment environment interface"
echo "4. Wait for the deployment to complete"
echo "5. Your application will be available at your-repl-name.your-username.repl.co"
echo ""

echo "Deployment preparation complete!"