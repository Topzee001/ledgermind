# LedgerMind Backend Microservices

This is the microservices backend for **LedgerMind** developed with Django REST Framework (DRF) leveraging TDD, built specifically for Interswitch's SME Accounting application.

## 🚀 Architecture

The application is structured as a collection of modular services:

| Port | Service | Description | DB Used / Core Dependency |
|------|---------|-------------|-------------|
| 8000 | **API Gateway** | Light-weight unified entrypoint proxy | Network Forwarder |
| 8001 | **User Service** | Auth, JWT, User profiles, Businesses | SQLite (Production PG) |
| 8002 | **Transaction Service** | Income/Expense & Bank CSV imports | SQLite, Cross-calls AI |
| 8003 | **AI Service** | OpenAI-powered classification & Rules | Environment Vars / Rules |
| 8004 | **Analytics Service** | Dashboard, Cashflow Forecasting, Credit Scoring | Cross-calls Transactions |
| 8005 | **Payment Service** | Interswitch Integration, Invoicing, Webhooks | SQLite, Interswitch API |

### Authentication Mechanism
Microservices communicate using two methods defined in the `/shared` util package:
- Client to Gateway: JWT Bearer Tokens (`Authorization: Bearer <TOKEN>`)
- Service to Service: Trusted secret key (`X-Service-Key: <SECRET>`)

## 💻 Prerequisites
- Python 3.9+ 
- Setup Virtual Env (`python3 -m venv venv && source venv/bin/activate`)
- Install deps: `pip install -r requirements.txt`

## 🏃 Running the Services locally

You have two options:
**Option 1: Using the provided bash script** 
```bash
# Starts all 6 servers using screen/background process logs
bash start_all.sh
```

**Option 2: Manually running them in separate terminals** (Replace 800X with respective port)
```bash
cd user_service
python manage.py runserver 8001
```

## 🧪 Testing (TDD approach)

Every service contains unit tests covering views, services, fallback logic, and mock external API integrations.

```bash
cd user_service && pytest -v
cd ../transaction_service && pytest -v
cd ../ai_service && pytest -v
cd ../analytics_service && pytest -v
cd ../payment_service && pytest -v
cd ../api_gateway && pytest -v
```

## 🌐 Endpoints via Gateway
- **Auth:** `POST http://localhost:8000/api/v1/users/register/` -> Creates User Accounts
- **Transactions:** `GET http://localhost:8000/api/v1/transactions/` -> Lists Ledger
- **Dashboard:** `GET http://localhost:8000/api/v1/analytics/dashboard/<uuid>/` -> Analytics Stats
- **Payments:** `POST http://localhost:8000/api/v1/payments/initiate/` -> Directs to Interswitch
