# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Start all services (builds images if needed)
docker-compose up -d

# Rebuild and start
docker-compose build && docker-compose up -d

# Stop all services
docker-compose down

# View logs (all or specific service)
docker-compose logs -f
docker-compose logs -f order-service

# Run a single service locally (requires local DB access)
cd user-service && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

No test suite or linter is configured. No Makefile exists.

## Architecture

Four FastAPI microservices communicating via synchronous REST (httpx.AsyncClient):

| Service | Port (host:container) | Database | Purpose |
|---------|----------------------|----------|---------|
| user-service | 8010:8000 | PostgreSQL (user_db) | Auth (JWT), user profiles, addresses |
| product-service | 8001:8001 | MongoDB (product_db) | Product catalog CRUD |
| inventory-service | 8002:8002 | PostgreSQL (inventory_db) | Stock tracking, reservations, audit history |
| order-service | 8003:8003 | MongoDB (order_db) | Order processing with multi-service validation |

**Service dependency graph:**
```
order-service → user-service (verify user)
order-service → product-service (get product details/pricing)
order-service → inventory-service (check/reserve/release stock)
product-service → inventory-service (auto-create inventory on product creation)
```

**Databases:** PostgreSQL 15 (shared instance, two DBs created via `postgres-init.sh`) and MongoDB 7. Neither is exposed to the host — services communicate over the Docker internal network.

## Service Code Layout (consistent across all four)

```
{service}/app/
├── main.py              # FastAPI app init, router registration
├── api/
│   ├── dependencies.py  # Auth/DB session injection via Depends()
│   └── routes/          # Route handlers
├── core/config.py       # Pydantic BaseSettings (env-driven)
├── db/database.py       # Connection setup (SQLAlchemy or Motor)
├── models/              # Domain models (SQLAlchemy ORM or Pydantic)
└── services/            # HTTP clients for inter-service calls
```

## Key Patterns

- **PostgreSQL services** (user, inventory): SQLAlchemy ORM with sync sessions, dependency-injected via `get_db()`
- **MongoDB services** (product, order): Motor async driver, database instance accessed via `get_database()`
- **Auth**: JWT with HS256 — access tokens (30min) and refresh tokens (7 days). Only user-service issues tokens; other services don't enforce auth
- **Inventory**: Dual-state tracking (available + reserved quantities) with full audit trail in `inventory_history` table
- **Order status machine**: PENDING → PAID → PROCESSING → SHIPPED → DELIVERED (or CANCELLED at any point). Cancellation triggers inventory release
- **Order creation**: Multi-step with rollback — reserves inventory per item and releases prior reservations if any step fails
- **Config**: All services use Pydantic `BaseSettings`; docker-compose environment variables override `.env` file defaults
- **API prefix**: All routes under `/api/v1/`
- **Health checks**: Every service exposes `/health`
