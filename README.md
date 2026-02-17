# MyCurrency

Web platform to calculate currency exchange rates.

Django REST API that provides real-time and historical currency exchange rates. Consumes data from external providers (CurrencyBeacon) and stores it locally for fast, resilient API access.

---

## Quick Start

```bash
# Start all services
docker-compose up

# Run migrations
docker-compose run --rm web python manage.py migrate

# Create superuser for admin access
docker-compose run --rm web python manage.py createsuperuser

# Access the application
# API: http://localhost:8000/api/v1/
# Admin: http://localhost:8000/admin/
# API Docs: http://localhost:8000/api/docs/
```

---

## Stack

- **Python 3.11**
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** (database)
- **Redis** (Celery broker)
- **Celery** + **Celery Beat** (async tasks)
- **Poetry** (dependency management)
- **Docker** + **Docker Compose**
- **drf-spectacular** (OpenAPI/Swagger)

---

## Architecture

**Domain-Driven Design (DDD) + Hexagonal Architecture**

```
apps/exchange/
├── api/v1/                    # API Layer (Controllers)
│   ├── serializers.py        # DRF Serializers
│   ├── views.py              # ViewSets
│   └── urls.py               # URL routing
├── application/               # Application Layer
│   ├── dto.py                # Data Transfer Objects
│   └── tasks.py              # Celery Tasks
├── domain/                    # Domain Layer (Business Logic)
│   ├── interfaces.py         # Contracts (ABC)
│   └── services.py           # Domain Services
└── infrastructure/            # Infrastructure Layer
    ├── persistence/
    │   ├── models.py         # Django ORM Models
    │   └── repositories.py   # Repository Pattern
    └── providers/
        ├── currency_beacon.py # CurrencyBeacon Adapter
        ├── mock.py           # Mock Provider
        └── registry.py       # Provider Registry
```

### Key Design Decisions

**Adapter Pattern for Providers**
- All providers implement `BaseExchangeRateProvider` interface
- New providers can be added without modifying existing code

**Fallback Chain Mechanism**
- Providers are ordered by priority (database field)
- If primary provider fails, system automatically tries next one
- Results are cached in database for fast subsequent access

**Concurrency for Historical Data**

Uses `asyncio` + `aiohttp` for I/O-bound operations instead of parallelism.

**Why concurrency over parallelism?**

The bottleneck is **network I/O** (waiting for HTTP responses), not CPU computation.

- **Concurrency (asyncio)**: Single thread handles dozens of simultaneous HTTP requests
- **Parallelism (multiprocessing)**: Multiple processes/threads for CPU-bound work

Since we're waiting on external APIs, concurrency maximizes throughput without the overhead of threads or processes. One thread can manage 50+ concurrent requests efficiently.

---

## Environment Variables

Create a `.env` file in the project root:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:pass@db:5432/exchange_db

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# CurrencyBeacon API
CURRENCY_BEACON_API_KEY=your-api-key-here
CURRENCY_BEACON_URL=https://api.currencybeacon.com/v1

# ExchangeRate
EXCHANGERATE_KEY=your-api-key-here
EXCHANGERATE_URL=https://v6.exchangerate-api.com/v6
```

---

## Development Setup

### Option 1: Docker (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Run migrations
docker-compose run --rm web python manage.py migrate

# Create superuser
docker-compose run --rm web python manage.py createsuperuser
```

### Option 2: Local Development (Not tested)

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Setup database (PostgreSQL must be running)
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start Redis (for Celery)
redis-server

# Start Celery worker (in another terminal)
celery -A core worker --loglevel=info

# Run development server
python manage.py runserver
```

---

## Loading Historical Data

Backfill historical exchange rate data for a date range.

### Command

```bash
# Asynchronous mode (recommended for large date ranges)
python manage.py load_historical --from 2024-01-01 --to 2024-12-31

# With Docker
docker-compose run --rm web python manage.py load_historical --from 2024-01-01 --to 2024-12-31

# Synchronous mode (useful for debugging)
python manage.py load_historical --from 2024-01-01 --to 2024-12-31 --sync
```

### How It Works

1. **Concurrent I/O**: Uses `asyncio` + `aiohttp` for concurrent HTTP requests
   - Fetches dozens of currency pairs simultaneously
   - Network I/O is the bottleneck, not CPU

2. **Smart Fetching**: For each date in the range:
   - Fetches rates for ALL currency pairs
   - Skips rates that already exist in database
   - Uses the provider fallback mechanism

3. **Efficient Storage**: Uses Django's `bulk_create()` to insert rates in batches

---

## API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **API Schema**: http://localhost:8000/api/schema/
- **ReDoc**: http://localhost:8000/api/redoc/

Main endpoints:
- `/api/v1/currencies/` - CRUD operations
- `/api/v1/rates/` - List rates
- `/api/v1/rates/time-series/` - Get time series data
- `/api/v1/rates/convert/` - Convert amount between currencies
- `/api/v1/providers/` - CRUD operations for providers

**Postman Collection**: `MyCurrency.postman_collection.json`

---

## Testing

```bash
# With Docker
docker-compose run --rm web python -m pytest tests/ -v

# Locally
python -m pytest tests/ -v
```

---

## Troubleshooting

### Docker Issues

```bash
# Rebuild containers
docker-compose build --no-cache

# Reset database
docker-compose down -v
docker-compose up
```

### Celery Not Working

```bash
# Check Redis is running
docker-compose ps redis

# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker
```

---

## Possible Improvements

### Performance & Scalability
- **Redis Caching**: Cache frequently accessed rates (EUR/USD, etc.) to reduce database queries
- **Rate Limiting**: Implement API throttling per user/IP to prevent abuse
- **Connection Pooling**: Optimize database connections for high traffic

### Security & Authentication
- **JWT Authentication**: Secure API endpoints with token-based authentication
- **API Keys**: Generate API keys for external consumers
- **HTTPS Only**: Enforce secure connections in production

### Features
- **WebSockets**: Real-time exchange rate updates for subscribed clients
- **API v2 with GraphQL**: Alternative query language for flexible data fetching
- **Multiple Base Currencies**: Support conversion between any currency pair, not just from one base
- **Historical Charts**: Visualize exchange rate trends over time

### DevOps & Monitoring
- **CI/CD Pipeline**: Automated testing and deployment with GitHub Actions
- **Monitoring**: Prometheus + Grafana for metrics and alerting
- **Logging**: Centralized logging with ELK stack (Elasticsearch, Logstash, Kibana)
- **Health Checks**: Endpoint monitoring and automated alerts

### Data & Providers
- **Additional Providers**: Integrate Fixer.io, Open Exchange Rates, ExchangeRate-API
- **Provider Health Dashboard**: Real-time status of all configured providers
- **Automatic Failover**: Smart detection and switching when providers fail
