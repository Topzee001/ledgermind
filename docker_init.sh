#!/usr/bin/env bash

# Exit on error
set -e

echo "🚀 Starting LedgerMind Docker Initialization..."

# 1. Build and start services in detached mode
echo "📦 Building and starting containers..."
docker-compose up -d --build

# 2. Function to run migrations for a service
run_migrate() {
    local service=$1
    echo "⚙️ Running migrations for $service..."
    docker-compose exec -T $service python manage.py migrate
}

# 3. Wait for DB to be healthy (simple sleep for now)
echo "⏳ Waiting for Database to be ready..."
sleep 5 

# 4. Run migrations for all 6 services
run_migrate user-service
run_migrate transaction-service
run_migrate ai-service
run_migrate analytics-service
run_migrate payment-service
run_migrate api-gateway

echo "All services are migrated and running!"
echo "API Gateway is available at: http://localhost:8000"
echo "User Service is available at: http://localhost:8001"
echo "Transaction Service is available at: http://localhost:8002"
