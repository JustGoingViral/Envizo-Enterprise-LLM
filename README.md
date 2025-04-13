# Enterprise LLM Platform

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Flask](https://img.shields.io/badge/framework-Flask-red)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-blue)
![Status](https://img.shields.io/badge/status-Production--Ready-brightgreen)

An on-premise, enterprise-ready platform for managing and deploying LLMs across multiple GPU server nodes. Features real-time analytics, fine-tuning capabilities, secure authentication, and full administrative control.


An on-premise, enterprise-ready platform for managing and deploying LLMs across multiple GPU server nodes. Features real-time analytics, fine-tuning capabilities, secure authentication, and full administrative control.

## ✨ Features

- 🔐 Role-based user authentication and API key system
- 🚀 Multi-GPU load balancing and server monitoring
- 📊 Real-time and historical analytics dashboard
- 🧠 Fine-tuning jobs with detailed metadata and tracking
- 🧱 Semantic caching, OpenAPI spec management, and backup system
- 🐘 PostgreSQL with SSL enforcement

## 🛠️ Tech Stack

- **Backend:** Flask (primary), FastAPI (optional fallback)
- **ORM:** SQLAlchemy (sync + async)
- **DB:** PostgreSQL
- **Auth:** JWT, OAuth2, Flask-Login
- **Deployment:** Gunicorn, cloud or self-hosted environment-ready
- **Metrics:** ServerLoadMetrics, Prometheus-compatible endpoint design

## ⚙️ Deployment

```bash
# Recommended for production
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

Set the following environment variables:

```env
ENVIRONMENT=production
DEBUG=false
SESSION_SECRET=your_secure_secret
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
```

## 🧪 Local Development

```bash
pip install -r requirements.txt
python start_server.py
```

## 📄 License

This project is licensed under the **GNU GPL v3.0**. See `LICENSE` for more info.
