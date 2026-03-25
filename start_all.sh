#!/bin/bash

# Simple script to boot all Django microservices in background

echo "Starting LedgerMind Microservices..."

source venv/bin/activate

# Create logs dir
mkdir -p logs

export SERVICE_SECRET_KEY="ledgermind-service-secret-dev"

# Run migrations and start services
for app in user_service transaction_service ai_service analytics_service payment_service api_gateway; do
    echo "Booting $app..."
    cd $app
    python3 manage.py makemigrations 
    python3 manage.py migrate
    
    PORT=""
    case $app in
        "api_gateway") PORT=8000 ;;
        "user_service") PORT=8001 ;;
        "transaction_service") PORT=8002 ;;
        "ai_service") PORT=8003 ;;
        "analytics_service") PORT=8004 ;;
        "payment_service") PORT=8005 ;;
    esac
    
    # Run the server in the background and pipe output to logs
    nohup python3 manage.py runserver $PORT > ../logs/${app}.log 2>&1 &
    
    cd ..
done

echo "✅ All 6 microservices started successfully!"
echo "➡️ API Gateway is listening on http://localhost:8000/"
echo "Check the 'logs/' folder to see the output of each service."
echo "To stop them later, run: pkill -f runserver"
