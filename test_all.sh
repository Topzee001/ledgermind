#!/bin/bash
# Simple script to run Pytest across all projects 

echo "Starting TDD Test Suite Execution..."

source venv/bin/activate

for app in api_gateway user_service transaction_service ai_service analytics_service payment_service; do
    echo "=========================================="
    echo "🧪 Testing $app..."
    echo "=========================================="
    cd $app
    pytest -v
    cd ..
done

echo "✅ All Tests executed!"
