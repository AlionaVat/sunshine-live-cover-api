# Music Archive Cover API

A FastAPI-based backend service for searching music tracks, retrieving metadata, artwork, and audio previews.

Developed for the Sunshine Live music archive project.

---

# Overview

Music Archive Cover API is a backend service designed to provide a unified access layer for the Sunshine Live music archive.

The service exposes REST endpoints for searching tracks, retrieving metadata, artwork, and audio preview resources from a centralized PostgreSQL repository.

Track discovery is powered by PostgreSQL `pg_trgm` similarity search, allowing reliable matching even when artist or title information is incomplete or contains minor variations.

The application is designed as an independent service with a clear separation between the API layer, database, and media assets, making it suitable for integration into existing backend environments.

---

# Key Features

- Fuzzy track search powered by PostgreSQL `pg_trgm`
- Metadata retrieval from a centralized PostgreSQL repository
- Artwork delivery in multiple resolutions
- Audio preview support
- RESTful API endpoints
- Protected web-based demo interface
- Interactive OpenAPI / Swagger documentation
- Modular backend architecture

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Language | Python 3 |
| Backend Framework | FastAPI |
| Database | PostgreSQL |
| Search | PostgreSQL `pg_trgm` |
| Database Driver | psycopg2 |
| API Documentation | OpenAPI / Swagger |
| Frontend | HTML / CSS |
| ASGI Server | Uvicorn |

---

# System Architecture

The application is organized into three main layers:

- **API Layer** – FastAPI application exposing REST endpoints.
- **Persistence Layer** – PostgreSQL database with `pg_trgm` similarity search.
- **Media Layer** – Artwork and audio resources referenced by the API.

The backend is designed as an independent service that can be integrated into existing environments without affecting other backend applications.

---

# Repository Structure

```text
Music_Archive_Cover_API_Handover/

├── source_code/
│   └── phase2/
│       ├── api/
│       │   ├── main.py
│       │   └── auth.py
│       │
│       ├── database/
│       │   └── schema.sql
│       │
│       └── scripts/
│           └── import_sqlite_to_postgres.py
│
├── docs/
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
│
├── screenshots/
├── samples/
│
├── README.md
├── HANDOVER.md
├── CHANGELOG.md
├── requirements.txt
├── .env.example
├── .gitignore
└── Dockerfile
```

---

# Getting Started

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure environment variables

Create a local `.env` file using the provided `.env.example` template.

## 3. Start the application

```bash
uvicorn phase2.api.main:app --reload
```

---

# Available Endpoints

| Endpoint | Description |
|-----------|-------------|
| `/health` | Service health check |
| `/cover` | Search tracks and retrieve metadata |
| `/demo` | Protected web demo interface |
| `/docs` | OpenAPI documentation |

---

# Documentation

Additional project documentation is available in the `docs` directory.

- API Reference
- Architecture Overview
- Deployment Guide

---

# Current Status

The current implementation provides the core functionality of the Music Archive Cover API and is ready for demonstration and further deployment.

### Completed

- ✅ FastAPI backend implementation
- ✅ PostgreSQL integration
- ✅ Fuzzy search using PostgreSQL `pg_trgm`
- ✅ Track metadata retrieval
- ✅ Artwork delivery (Small / Medium / Large)
- ✅ Audio preview support
- ✅ Protected demo interface
- ✅ OpenAPI / Swagger documentation
- ✅ Database schema and migration script
- ✅ Project documentation

### Deployment Readiness

The application has been prepared for deployment as an independent backend service.

Following the recommendation from the DevOps team, the service should be deployed separately from the existing backend infrastructure to ensure clear separation of responsibilities and minimize impact on production systems.

---

# License

This project was developed for internal use as part of the Sunshine Live music archive project.
