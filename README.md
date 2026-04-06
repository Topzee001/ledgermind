# 🛡️ LedgerMind Backend Microservices

This is the microservices backend for **LedgerMind**, an SME Accounting application leveraging TDD and Interswitch integrations. Built with Django REST Framework (DRF) and orchestrated with Docker.

---

## 🚀 Quick Start (Dockerized Workflow)

The fastest way to get LedgerMind up and running is using Docker. This spins up all 6 microservices and a dedicated PostgreSQL database automatically.

### 1. Requirements
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS, Windows, or Linux)

### 2. Initialization
Run the provided setup script to build images, start containers, and apply all database migrations:
```bash
chmod +x docker_init.sh
./docker_init.sh
```

### 3. Verify Services
The services will be available at the followings ports:
| Port | Service | Entrypoint URL |
|------|---------|-------------|
| **8000** | **API Gateway** | `http://localhost:8000` |
| 8001 | User Service | `http://localhost:8001` |
| 8002 | Transaction Service | `http://localhost:8002` |
| 8003 | AI Service | `http://localhost:8003` |
| 8004 | Analytics Service | `http://localhost:8004` |
| 8005 | Payment Service | `http://localhost:8005` |

---

## 🛠️ Architecture Details

LedgerMind is structured as a collection of modular services that talk to each other over an internal Docker network.

*   **API Gateway:** The single entry point for all frontend requests. It routes traffic to the appropriate service.
*   **Shared Module:** A common utility package located in `/shared` that provides consistent authentication (`ServiceToServiceAuth`), exceptions, and pagination across all services.
*   **Database:** A single shared PostgreSQL 15 container for all microservices (optimized for development).

---

## 🧪 Testing with Postman/cURL

To test if everything is working, try registering a new user through the **API Gateway**:

**Endpoint:** `POST http://localhost:8000/api/v1/users/register/`

**Request Body (JSON):**
```json
{
    "email": "dev@ledgermind.io",
    "password": "StrongPassword123!",
    "first_name": "Ledger",
    "last_name": "Mind",
    "business_name": "LedgerMind Corp"
}
```

---

## 🔧 Manual Setup (Traditional Way)

If you prefer not to use Docker, follow these steps:

1.  **Setup Virtual Env:** `python3 -m venv venv && source venv/bin/activate`
2.  **Install dependencies:** `pip install -r requirements.txt`
3.  **Start all services:** `bash start_all.sh`

---

## 🚦 Troubleshooting
*   **Port in use:** If you see "Port is already allocated", run `docker-compose down --remove-orphans` to clear old processes.
*   **DB Migration Errors:** Ensure you've run `./docker_init.sh` to initialize the PostgreSQL database schema.
