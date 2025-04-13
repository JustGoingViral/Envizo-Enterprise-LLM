import os
import random
import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any, Tuple

# Intelligently and professionally funny error messages
ERROR_MESSAGES = [
    "Well, that wasn't supposed to happen. Our GPUs are having an existential crisis. Engineers dispatched with philosophical remedies.",
    "Looks like our LLM tried to understand quantum mechanics and got confused. We've sent it back to physics school.",
    "Error 42: The answer to everything... except why this happened. Our tech wizards are deciphering the cosmic glitch.",
    "Houston, we have a problem. Actually, our server has a problem. Houston is fine. Tech team is investigating while humming 'Space Oddity'.",
    "The bits and bytes had a disagreement. We've called in an AI mediator to resolve their differences.",
    "Our server decided to take an unscheduled meditation break. We're gently coaxing it back to reality with enterprise-grade incense.",
    "The system tried to divide by zero again. We've reminded it about the laws of mathematics and universe integrity.",
    "Your request encountered a temporal anomaly. Don't worry, our time-traveling debug team was dispatched yesterday.",
    "The database wanted to see other applications. We're in relationship counseling now. Please try again when we've reconciled.",
    "Looks like our GPU tried overclocking itself and got a little too excited. We're applying cooling logic and calming techniques.",
    "The model hallucinated that it was on vacation in the Bahamas. We've shown it pictures of server racks to bring it back to reality.",
    "You've discovered our hidden feature: Random Error Generation™. Unfortunately, it wasn't supposed to be activated yet.",
    "Our AI tried to optimize the system by removing all the 'unnecessary' code. Turns out, it was actually quite necessary.",
    "Error: Coffee levels critically low in development team. Caffeine replenishment in progress. Please stand by.",
    "The server attempted multi-dimensional processing without its safety goggles. We've equipped it properly and are trying again."
]

# Configure logging based on environment
environment = os.environ.get('ENVIRONMENT', 'development')
log_level = logging.DEBUG if environment == 'development' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add warnings about logging level in production
if environment == 'production' and log_level == logging.DEBUG:
    logger.warning("Debug logging is enabled in production environment. This may expose sensitive information.")
    logger.warning("Consider setting ENVIRONMENT to 'production' and ensuring DEBUG is set to 'False'.")

# Import config settings
from config import settings

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY  # Already handles default case in config.py
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URL  # Already handles default case in config.py
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

# Import models and database functions
from database import init_db
from models import User, LLMModel, Query, ApiKey, ServerNode, ServerLoadMetrics

@login_manager.user_loader
def load_user(user_id):
    """Load a user using the ID stored in the session"""
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        return None

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', title="Enterprise LLM Platform")

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Render the login page and handle login form submission"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validate user credentials
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', title="Login")

@app.route('/admin')
@login_required
def admin_page():
    """Render the admin page"""
    # Check if user is admin
    if current_user.role.name != "ADMIN":
        flash('You do not have permission to access admin page', 'error')
        return redirect(url_for('index'))
    
    return render_template('admin.html', title="Admin Dashboard", now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/analytics')
@login_required
def analytics_page():
    """Render the analytics page"""
    return render_template('analytics.html', title="Analytics Dashboard")

@app.route('/fine-tuning')
@login_required
def fine_tuning_page():
    """Render the fine-tuning page"""
    return render_template('fine_tuning.html', title="Fine-Tuning Dashboard")

@app.route('/logout')
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/api/health')
def health_check():
    """Health check endpoint with database connection test"""
    status = "ok"
    db_status = "ok"
    message = "All systems operational"
    error = None
    
    try:
        # Test database connection by executing a simple query
        # This will verify both sync and async connections are working
        db.session.execute(db.text("SELECT 1")).scalar()
    except Exception as e:
        db_status = "error"
        status = "degraded"
        message = "Database connection issue detected"
        error = str(e)
        logger.error(f"Health check database error: {str(e)}")
    
    response = {
        "status": status,
        "components": {
            "api": "ok",
            "database": db_status
        },
        "timestamp": datetime.now().isoformat(),
        "message": message
    }
    
    if error:
        response["error"] = error
    
    return jsonify(response)

@app.route('/api/gpu/utilization')
@login_required
def gpu_utilization():
    """Get real-time GPU utilization data for all server nodes"""
    try:
        # Get all active server nodes
        servers = db.session.execute(
            db.select(ServerNode).where(ServerNode.is_active == True)
        ).scalars().all()
        
        # If no servers, return empty data
        if not servers:
            return jsonify({
                "status": "success",
                "message": "No active GPU servers available",
                "data": [],
                "timestamp": datetime.now().isoformat()
            })
            
        # Create the response data
        server_data = []
        
        for server in servers:
            # Get the latest metrics for this server
            latest_metrics = db.session.execute(
                db.select(ServerLoadMetrics)
                .where(ServerLoadMetrics.server_id == server.id)
                .order_by(ServerLoadMetrics.timestamp.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            # If we have metrics, include them
            if latest_metrics:
                server_data.append({
                    "server_id": server.id,
                    "server_name": server.name,
                    "gpu_count": server.gpu_count,
                    "gpu_memory_total": server.gpu_memory,
                    "health_status": server.health_status,
                    "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None,
                    "gpu_utilization": latest_metrics.gpu_utilization,
                    "gpu_memory_used": latest_metrics.gpu_memory_used,
                    "cpu_utilization": latest_metrics.cpu_utilization,
                    "active_requests": latest_metrics.active_requests,
                    "queue_depth": latest_metrics.queue_depth,
                    "timestamp": latest_metrics.timestamp.isoformat()
                })
            else:
                # Include server with empty metrics
                server_data.append({
                    "server_id": server.id,
                    "server_name": server.name,
                    "gpu_count": server.gpu_count,
                    "gpu_memory_total": server.gpu_memory,
                    "health_status": server.health_status,
                    "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None,
                    "gpu_utilization": 0.0,
                    "gpu_memory_used": 0.0,
                    "cpu_utilization": 0.0,
                    "active_requests": 0,
                    "queue_depth": 0,
                    "timestamp": datetime.now().isoformat()
                })
                
        return jsonify({
            "status": "success",
            "message": f"Retrieved data for {len(server_data)} servers",
            "data": server_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        logger.error(f"Error ID: {error_id} - Error getting GPU utilization data: {str(e)}")
        funny_message = random.choice(ERROR_MESSAGES)
        return jsonify({
            "status": "error",
            "error_id": error_id,
            "message": funny_message,
            "technical_details": str(e) if environment == 'development' else "Check logs for details.",
            "data": [],
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/gpu/seed-demo-data')
@login_required
def seed_gpu_demo_data():
    """Seed some sample data for demonstration purposes"""
    try:
        # Create a default server if none exists
        server = db.session.execute(
            db.select(ServerNode).where(ServerNode.name == "default-gpu-server")
        ).scalar_one_or_none()
        
        if not server:
            server = ServerNode(
                name="default-gpu-server",
                host="localhost",
                port=8080,
                gpu_count=4,
                gpu_memory=24,
                is_active=True,
                health_status="healthy",
                last_health_check=datetime.now()
            )
            db.session.add(server)
            db.session.commit()
            logger.info(f"Created demo server: {server.name}")
        
        # Create a second server for demonstration
        server2 = db.session.execute(
            db.select(ServerNode).where(ServerNode.name == "secondary-gpu-server")
        ).scalar_one_or_none()
        
        if not server2:
            server2 = ServerNode(
                name="secondary-gpu-server",
                host="192.168.1.101",
                port=8080,
                gpu_count=2,
                gpu_memory=16,
                is_active=True,
                health_status="healthy",
                last_health_check=datetime.now()
            )
            db.session.add(server2)
            db.session.commit()
            logger.info(f"Created demo server: {server2.name}")
        
        # Add some metrics
        server_ids = [server.id, server2.id]
        
        # Clear existing metrics for demo
        db.session.execute(db.delete(ServerLoadMetrics).where(ServerLoadMetrics.server_id.in_(server_ids)))
        db.session.commit()
        
        # Add current metrics
        metrics1 = ServerLoadMetrics(
            server_id=server.id,
            timestamp=datetime.now(),
            gpu_utilization=78.5,  # Higher load on primary
            gpu_memory_used=18.2,
            gpu_memory_total=24.0,
            cpu_utilization=45.0,
            active_requests=12,
            queue_depth=3
        )
        
        metrics2 = ServerLoadMetrics(
            server_id=server2.id,
            timestamp=datetime.now(),
            gpu_utilization=35.2,  # Lower load on secondary
            gpu_memory_used=6.8,
            gpu_memory_total=16.0,
            cpu_utilization=28.0,
            active_requests=4,
            queue_depth=0
        )
        
        db.session.add(metrics1)
        db.session.add(metrics2)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Demo data seeded successfully",
            "servers": [
                {"id": server.id, "name": server.name},
                {"id": server2.id, "name": server2.name}
            ],
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        error_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        logger.error(f"Error ID: {error_id} - Error seeding demo data: {str(e)}")
        funny_message = random.choice(ERROR_MESSAGES)
        return jsonify({
            "status": "error",
            "error_id": error_id,
            "message": funny_message,
            "technical_details": str(e) if environment == 'development' else "Check logs for details.",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/seed-all-data')
@login_required
def seed_all_data():
    """Seed all data for the application"""
    try:
        # Check if user is admin
        if current_user.role.name != "ADMIN":
            flash('You do not have permission to seed data', 'error')
            return redirect(url_for('index'))
        
        # Import and use the seeder
        from seed_data import seed_all_data
        result = seed_all_data()
        
        return jsonify({
            "status": result["status"],
            "message": result["message"],
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        error_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        logger.error(f"Error ID: {error_id} - Error seeding all data: {str(e)}")
        funny_message = random.choice(ERROR_MESSAGES)
        return jsonify({
            "status": "error",
            "error_id": error_id,
            "message": funny_message,
            "technical_details": str(e) if environment == 'development' else "Check logs for details.",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/gpu/history/<int:server_id>')
@login_required
def gpu_utilization_history(server_id):
    """Get historical GPU utilization data for a specific server"""
    try:
        # Get the server
        server = db.session.get(ServerNode, server_id)
        if not server:
            return jsonify({
                "status": "error",
                "message": f"Server with ID {server_id} not found",
                "data": [],
                "timestamp": datetime.now().isoformat()
            }), 404
            
        # Get historical metrics (last 24 hours)
        one_day_ago = datetime.now() - timedelta(days=1)
        
        metrics = db.session.execute(
            db.select(ServerLoadMetrics)
            .where(
                ServerLoadMetrics.server_id == server_id,
                ServerLoadMetrics.timestamp >= one_day_ago
            )
            .order_by(ServerLoadMetrics.timestamp.asc())
        ).scalars().all()
        
        # Format the metrics for the response
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                "timestamp": metric.timestamp.isoformat(),
                "gpu_utilization": metric.gpu_utilization,
                "gpu_memory_used": metric.gpu_memory_used,
                "gpu_memory_total": metric.gpu_memory_total,
                "cpu_utilization": metric.cpu_utilization,
                "active_requests": metric.active_requests,
                "queue_depth": metric.queue_depth
            })
            
        return jsonify({
            "status": "success",
            "message": f"Retrieved {len(metrics_data)} historical metrics for server {server.name}",
            "server_name": server.name,
            "data": metrics_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        logger.error(f"Error ID: {error_id} - Error getting GPU utilization history: {str(e)}")
        funny_message = random.choice(ERROR_MESSAGES)
        return jsonify({
            "status": "error",
            "error_id": error_id,
            "message": funny_message,
            "technical_details": str(e) if environment == 'development' else "Check logs for details.",
            "data": [],
            "timestamp": datetime.now().isoformat()
        }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all exceptions with professional error messages"""
    # Generate a unique error ID for tracking
    error_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    
    # Log the error with the ID for tracking
    logger.error(f"Error ID: {error_id} - Type: {type(e).__name__} - Message: {str(e)}")
    
    # Include stack trace in development mode
    if environment == 'development':
        import traceback
        logger.debug(f"Traceback for error {error_id}:\n{traceback.format_exc()}")
    
    if request.path.startswith('/api/'):
        # Return JSON for API requests with more details in development
        response = {
            "status": "error",
            "error_id": error_id,
            "message": random.choice(ERROR_MESSAGES),
            "timestamp": datetime.now().isoformat()
        }
        
        # Include error details in development mode
        if environment == 'development':
            response["error_type"] = type(e).__name__
            response["error_details"] = str(e)
            
        return jsonify(response), 500
    else:
        # Render an error template for web requests
        error_context = {
            "error_id": error_id,
            "error_message": random.choice(ERROR_MESSAGES),
            "timestamp": datetime.now().isoformat()
        }
        
        # Include error details in development mode
        if environment == 'development':
            error_context["error_type"] = type(e).__name__
            error_context["error_details"] = str(e)
            
        return render_template('error.html', **error_context), 500

# Initialize database and create tables
with app.app_context():
    db.create_all()
    
    # Create admin user if none exists
    admin = db.session.execute(db.select(User).filter_by(username='admin')).scalar_one_or_none()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            full_name='Admin User',
            password_hash=generate_password_hash('admin'),
            role='ADMIN'
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Created admin user")

# Models were already imported above

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)