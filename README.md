# ODP --- Gmail-Native RAG Assistant

ODP (Outbound Deal Processor) is a Gmail-native AI co-pilot that drafts
accurate, founder-tone replies to investor questions using deal-approved
knowledge.\
The system ensures responses are grounded strictly in verified deal data
and approved FAQs.

------------------------------------------------------------------------

# 🚀 Tech Stack

-   Python 3.10+
-   Flask (Factory Pattern)
-   Flask-SQLAlchemy
-   Flask-Migrate (Alembic)
-   PostgreSQL
-   python-decouple (.env management)
-   JSONB support (PostgreSQL)

------------------------------------------------------------------------

# 📂 Main Files Structure

    Source Code/
    │
    ├── migrations/                # Alembic migration files
    │
    ├── odp/
    │   ├── app.py                 # Application factory
    │   ├── __init__.py
    │   ├── requirements.txt	
    │   │
    │   ├── base/
    │   │   └── constants.py
    │   │
    │   ├── config/
    │   │   ├── database.py
    │   │   ├── swagger.py
    │   │   └── urls.py
    │   │
    │   ├── models/
    │   │   ├── odp_deal.py
    │   │   ├── odp_deal_term.py
    │   │   ├── odp_deal_document.py
    │   │   ├── odp_faq.py
    │   │   ├── odp_tone_rule.py
    │   │   ├── odp_deal_dynamic_fact.py
    │   │   ├── odp_reply_log.py
    │   │   └── __init__.py
	│   │
    │   ├── vendors/
    │   │   ├── aws > s3_uploader.py
	│   │
    │   ├── util/
    │   │   ├── exceptions.py
    │   │   ├── messages.py
	│   │	
    └── .env

------------------------------------------------------------------------

# ⚙️ Local Setup Guide

## 1️⃣ Clone Repository

``` bash
mkdir "Source Code"
cd "Source Code"
git clone <repo-url>
```

------------------------------------------------------------------------

## 2️⃣ Create Virtual Environment

``` bash
python -m venv .venv
```

Activate:

### Windows

``` bash
.venv\Scripts\activate
```

### Mac/Linux

``` bash
source .venv/bin/activate
```

------------------------------------------------------------------------

## 3️⃣ Install Dependencies

If `requirements.txt` exists:

``` bash
pip install -r requirements.txt
```

Otherwise:

``` bash
pip install Flask Flask-SQLAlchemy Flask-Migrate psycopg2-binary python-decouple python-dotenv
```

------------------------------------------------------------------------

## 4️⃣ Setup PostgreSQL

Create database:

``` sql
CREATE DATABASE odp;
```

------------------------------------------------------------------------

## 5️⃣ Configure Environment Variables

Create `.env` file in project root:

    APP_ENV=development
    APP_SECRET_KEY=your_secret_key

    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=odp_db
    DB_USER=postgres
    DB_PASSWORD=your_password

    FLASK_APP=app:create_app

------------------------------------------------------------------------

## 6️⃣ Run Database Migrations

If fresh setup:

``` bash
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

If migrations already exist:

``` bash
flask db upgrade
```

------------------------------------------------------------------------

## 7️⃣ Run Application

``` bash
flask --app odp.app:create_app run
```

Server will run at:

    http://127.0.0.1:5000

------------------------------------------------------------------------

# 🗃️ Database Schema Overview

### Core Tables

-   odp_deals
-   odp_deal_terms
-   odp_deal_documents
-   odp_faqs
-   odp_tone_rules
-   odp_deal_dynamic_facts
-   odp_reply_logs
-   alembic_version

------------------------------------------------------------------------

# 🧪 Migration Workflow

Whenever adding or modifying models:

``` bash
flask --app odp.app:create_app db migrate -m "describe change"
flask --app odp.app:create_app db upgrade
```

To rollback one migration:

``` bash
flask db downgrade -1
```

------------------------------------------------------------------------

# 🛡️ System Design Principles

-   All answers must come from approved Knowledge Base
-   No hallucinated deal terms
-   Clarify-first behavior if information is missing
-   Founder-tone enforcement
-   Full audit logging for trust and debugging

------------------------------------------------------------------------

# 👨‍💻 Development Guidelines

-   Always register new models inside `models/__init__.py`
-   Never delete `alembic_version` table
-   Do not modify migration files after production release
-   Always create new migration for schema changes
-   Use feature branches for development

------------------------------------------------------------------------

# 🔒 Production Notes

-   Use Gunicorn or another WSGI server
-   Disable debug mode
-   Store secrets securely (environment variables or secret manager)
-   Use managed PostgreSQL (e.g., AWS RDS)

------------------------------------------------------------------------

# 📞 Support

For technical issues, contact the ODP Engineering Team.
