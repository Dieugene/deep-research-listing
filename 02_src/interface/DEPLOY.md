# Deployment Guide

## Prerequisites
- Docker + Docker Compose installed
- `listing_research.db` generated (run `python tools/export_to_sqlite.py` from project root)

## First deploy
```bash
cd 02_src/interface
docker-compose up --build -d
```

## Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health

## Update data (new jurisdictions added)
```bash
# 1. Regenerate the database (from project root)
python tools/export_to_sqlite.py

# 2. Restart only the backend
cd 02_src/interface
docker-compose restart backend
```

## Rebuild after code changes
```bash
docker-compose up --build -d
```
