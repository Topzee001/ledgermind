"""
Dashboard Analytics API endpoint.

CACHING NOTE:
  This view itself is READ-only — it just calls fetch_business_transactions()
  which already handles caching internally (see services.py).
  No additional cache logic is needed here.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from collections import defaultdict
from .services import fetch_business_transactions


class DashboardDataView(APIView):
    """
    Get aggregated dashboard data for a business.

    GET /api/v1/analytics/dashboard/{business_id}/

    Response is derived from cached transaction data (up to 5 min stale).
    """
    def get(self, request, business_id):
        transactions = fetch_business_transactions(business_id)

        total_income = 0
        total_expense = 0
        category_breakdown = defaultdict(float)
        monthly_trends = defaultdict(lambda: {"income": 0, "expense": 0})

        for txn in transactions:
            txn_date = txn.get("date", "")[:7]  # YYYY-MM
            amount = float(txn.get("amount", 0))
            is_income = txn.get("type") == "income"
            category_name = txn.get("category_detail", {}).get("name", "Uncategorized")

            if is_income:
                total_income += amount
                monthly_trends[txn_date]["income"] += amount
            else:
                total_expense += amount
                category_breakdown[category_name] += amount
                monthly_trends[txn_date]["expense"] += amount

        net_profit = total_income - total_expense

        data = {
            "overview": {
                "total_income": total_income,
                "total_expense": total_expense,
                "net_profit": net_profit,
            },
            "expense_by_category": dict(category_breakdown),
            "monthly_trends": dict(monthly_trends),
        }

        return Response({"success": True, "data": data})
