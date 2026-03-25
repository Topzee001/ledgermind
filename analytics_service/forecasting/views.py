"""Forecasting service views."""
from rest_framework.views import APIView
from rest_framework.response import Response
import statistics
from dashboard.services import fetch_business_transactions
from datetime import datetime
from collections import defaultdict


class CashflowForecastView(APIView):
    """
    Predict next 3 months of cashflow using moving average logic.
    
    GET /api/v1/analytics/forecasting/cashflow/{business_id}/
    """
    def get(self, request, business_id):
        transactions = fetch_business_transactions(business_id)
        
        monthly_net = defaultdict(float)
        monthly_income = defaultdict(float)
        monthly_expense = defaultdict(float)

        for txn in transactions:
            txn_date = txn.get('date', '')[:7] # YYYY-MM
            amount = float(txn.get('amount', 0))
            if txn.get('type') == 'income':
                monthly_income[txn_date] += amount
                monthly_net[txn_date] += amount
            else:
                monthly_expense[txn_date] += amount
                monthly_net[txn_date] -= amount

        # Basic prediction: average of past 3 active months
        sorted_months = sorted(monthly_net.keys())
        latest_months = sorted_months[-3:] if sorted_months else []
        
        avg_income = 0
        avg_expense = 0
        if latest_months:
            avg_income = statistics.mean([monthly_income[m] for m in latest_months])
            avg_expense = statistics.mean([monthly_expense[m] for m in latest_months])

        # Forecast next 3 months statically based on avg
        # (This would be more complex with ML/AI forecasting)
        forecasts = []
        for i in range(1, 4):
            forecasts.append({
                'month': f"Month +{i}",
                'projected_income': round(avg_income, 2),
                'projected_expense': round(avg_expense, 2),
                'projected_net': round(avg_income - avg_expense, 2)
            })

        return Response({
            'success': True,
            'data': forecasts
        })
