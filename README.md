# 💱 MyCurrency

**Web platform to calculate currency exchange rates**

MyCurrency is a Django REST API that provides real-time and historical currency exchange rates. It consumes data from external providers (CurrencyBeacon) and stores it locally for fast, resilient API access. The system is designed to be extensible: new providers can be added by implementing an interface and registering them, without modifying existing logic.

---

## 🚀 Quick Start

```bash
# Clone and navigate
cd MyCurrency

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

## 📚 Stack & Architecture

### Technology Stack
- **Python 3.11**
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** (database)
- **Redis** (Celery broker)
- **Celery** + **Celery Beat** (async tasks & scheduling)
- **Poetry** (dependency management)
- **Docker** + **Docker Compose**
- **drf-spectacular** (OpenAPI/Swagger documentation)

### Architecture Pattern

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
│   ├── models.py             # Domain Models
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

**🔄 Adapter Pattern for Providers**
- All providers implement `BaseExchangeRateProvider` interface
- New providers can be added without modifying existing code
- Providers are registered via enum → class mapping

**🔗 Fallback Chain Mechanism**
- Providers are ordered by priority (database field)
- If primary provider fails, system automatically tries next one
- Results are cached in database for fast subsequent access

**🆔 UUID Primary Keys**
- All models use UUIDs instead of sequential integers
- Prevents ID enumeration attacks
- Facilitates future distributed systems

**⚡ Concurrency for Historical Data**
- Uses `asyncio` + `aiohttp` for I/O-bound operations
- Allows dozens of simultaneous HTTP requests without threading overhead
- **Why asyncio?** The bottleneck is network I/O, not CPU computation

---

## 🌐 Supported Currencies

- **EUR** - Euro (€)
- **USD** - US Dollar ($)
- **GBP** - British Pound (£)
- **CHF** - Swiss Franc (CHF)

Currencies are seeded via database migrations.

---

## 📡 API Endpoints

### Base URL: `/api/v1/exchange/`

#### **Currencies**
```http
GET    /currencies/           # List all currencies
POST   /currencies/           # Create currency
GET    /currencies/{id}/      # Get currency details
PUT    /currencies/{id}/      # Update currency
DELETE /currencies/{id}/      # Delete currency
```

#### **Exchange Rates**
```http
GET    /rates/                # List all rates
GET    /rates/{id}/           # Get rate details

# Custom Actions:
GET    /rates/time-series/    # Get time series data
GET    /rates/convert/        # Convert amount
```

**Time Series Example:**
```http
GET /rates/time-series/?source_currency=EUR&date_from=2024-01-01&date_to=2024-01-31

Response:
{
  "source_currency": "EUR",
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "rates": [
    {
      "source_currency": {"code": "EUR", ...},
      "exchanged_currency": {"code": "USD", ...},
      "rate_value": "1.085200",
      "valuation_date": "2024-01-01"
    },
    ...
  ]
}
```

**Convert Amount Example:**
```http
GET /rates/convert/?source_currency=EUR&exchanged_currency=USD&amount=100

Response:
{
  "source_currency": "EUR",
  "exchanged_currency": "USD",
  "amount": "100",
  "rate": "1.085200",
  "converted_amount": "108.520000",
  "valuation_date": "2024-02-16"
}
```

#### **Providers**
```http
GET    /providers/            # List all providers
POST   /providers/            # Create provider
GET    /providers/{id}/       # Get provider details
PUT    /providers/{id}/       # Update provider (priority, is_active)
DELETE /providers/{id}/       # Delete provider
```

---

## 🔑 Environment Variables

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
```

---

## 🔧 Development Setup

### Option 1: Docker (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Run migrations
docker-compose run --rm web python manage.py migrate

# Create superuser
docker-compose run --rm web python manage.py createsuperuser

# Access services:
# - API: http://localhost:8000/api/v1/
# - Admin: http://localhost:8000/admin/
# - API Docs: http://localhost:8000/api/docs/
```

### Option 2: Local Development

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

# Start Celery beat (in another terminal)
celery -A core beat --loglevel=info

# Run development server
python manage.py runserver
```

---

## 🤖 Celery Tasks & Scheduling

### Background Tasks

The system includes several Celery tasks for data synchronization:

1. **`sync_exchange_rates_for_today()`**
   - Syncs rates for all currency pairs for today
   - Scheduled daily at 00:30 UTC

2. **`cleanup_old_exchange_rates(days_to_keep=90)`**
   - Removes rates older than 90 days
   - Scheduled weekly on Sundays at 02:00 UTC

3. **`check_providers_health()`**
   - Tests all providers with USD→EUR conversion
   - Scheduled every 6 hours

4. **`sync_missing_rates_for_currency_pair(source, target, date_from, date_to)`**
   - Fills gaps in historical data for specific pair
   - Can be triggered manually

### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    'sync-rates-daily': {
        'task': 'sync_exchange_rates_for_today',
        'schedule': crontab(hour=0, minute=30),
    },
    'cleanup-old-rates': {
        'task': 'cleanup_old_exchange_rates',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
        'kwargs': {'days_to_keep': 90},
    },
    'check-providers-health': {
        'task': 'check_providers_health',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}
```

---

## 🎭 Admin Panel

Access at: **http://localhost:8000/admin/**

### Features

1. **Currency Management**
   - CRUD operations for currencies
   - Search and filter capabilities

2. **Exchange Rates**
   - View all stored rates
   - Filter by date, currency pair
   - Date hierarchy for easy navigation

3. **Provider Management**
   - Configure provider priority
   - Activate/deactivate providers
   - Bulk actions for status changes

4. **💱 Currency Converter Tool**
   - **URL:** `/admin/exchange/converter/`
   - Interactive converter with:
     - Select source currency
     - Choose multiple target currencies
     - Specify amount
     - Optional date selection
     - Real-time conversion using fallback mechanism

---

## 🧪 Testing

### Run All Tests

```bash
# With Docker
docker-compose run --rm web python -m pytest tests/ -v

# Locally
python -m pytest tests/ -v
```

### Test Coverage

```
108 tests passing:
- Providers (MockProvider, CurrencyBeacon, Registry): 19 tests
- Domain Services: 11 tests
- Repositories: 23 tests
- Serializers: 10 tests
- API Views: 22 tests
- Celery Tasks: 11 tests
- DTOs: 12 tests
```

### Test Structure

```
tests/
├── apps/exchange/
│   ├── api/v1/
│   │   ├── test_serializers.py
│   │   └── test_views.py
│   ├── application/
│   │   ├── test_dto.py
│   │   └── test_tasks.py
│   ├── domain/
│   │   └── test_services.py
│   └── infrastructure/
│       ├── persistence/
│       │   └── test_repositories.py
│       └── providers/
│           ├── test_currency_beacon.py
│           ├── test_mock.py
│           └── test_registry.py
```

---

## 📊 Data Flow

### Rate Retrieval Flow

```
1. API Request → ViewSet
2. ViewSet → Domain Service (ExchangeRateService)
3. Service checks Database first
   ├─ Found → Return immediately
   └─ Not found → Query Providers
4. Provider Registry returns active providers by priority
5. Service tries each provider in order
   ├─ Provider 1 succeeds → Save to DB → Return
   └─ Provider 1 fails → Try Provider 2 → ...
6. If all fail → Return None
```

### Provider Fallback Example

```
Configuration in DB:
- CurrencyBeacon (priority=1, active=true)
- MockProvider (priority=2, active=true)

Flow:
1. Check DB → Not found
2. Try CurrencyBeacon (priority 1)
   └─ Timeout/Error → Next
3. Try MockProvider (priority 2)
   └─ Success → Save & Return
```

---

## 🚀 Possible Improvements

### Short Term
- **Hourly Granularity:** Support intraday rates
- **Redis Caching:** Cache hot rates (EUR/USD, etc.)
- **Rate Limiting:** Throttle API requests per user
- **Webhooks:** Notify external services on rate updates

### Medium Term
- **JWT Authentication:** Secure API with tokens
- **API v2:** GraphQL interface
- **More Providers:** Add Fixer.io, Open Exchange Rates
- **Currency Autocomplete:** Frontend-friendly search

### Long Term
- **CI/CD Pipeline:** GitHub Actions + automated deployment
- **Monitoring:** Prometheus + Grafana dashboards
- **Multi-region:** Deploy to multiple data centers
- **Historical Analytics:** Trend analysis & predictions

---

## 📝 License

This project is for educational purposes.

---

## 👤 Author

Built with ❤️ by Emmanuel using Django + DRF

---

## 🤝 Contributing

This is an educational project, but suggestions and improvements are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📖 Additional Documentation

- **API Documentation:** http://localhost:8000/api/docs/ (Swagger UI)
- **API Schema:** http://localhost:8000/api/schema/ (OpenAPI 3.0)
- **ReDoc:** http://localhost:8000/api/redoc/ (Alternative API docs)

---

## 🐛 Troubleshooting

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

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Reset database
docker-compose run --rm web python manage.py migrate --run-syncdb
```

---

**Happy Currency Converting! 💱**
