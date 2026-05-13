"""Credit Readiness Score views."""
from rest_framework.views import APIView
from rest_framework.response import Response
from dashboard.services import fetch_business_transactions


class CreditScoreView(APIView):
    """
    Calculates a simple business credit readiness score 1-100 based on history.
    
    GET /api/v1/analytics/credit-score/{business_id}/
    """
    def get(self, request, business_id):
        refresh = request.query_params.get("refresh", "false").lower() == "true"
        transactions = fetch_business_transactions(business_id, force_refresh=refresh)
        
        # Very basic rules algorithm:
        # Base score 50
        # +2 for every income transaction
        # +10 if avg income > avg expense
        # +5 per active month
        # Capped at 99 for Hackathon demonstration
        
        if not transactions:
            return Response({'success': True, 'data': {'score': 0, 'rating': 'Poor (No data)'}})
            
        income_count = sum(1 for t in transactions if t.get('type') == 'income')
        months_active = len(set(t.get('date', '')[:7] for t in transactions))
        
        total_income = sum(float(t.get('amount', 0)) for t in transactions if t.get('type') == 'income')
        total_expense = sum(float(t.get('amount', 0)) for t in transactions if t.get('type') == 'expense')
        
        score = 50 + (income_count * 2) + (months_active * 5)
        if total_income > total_expense:
            score += 10
            
        score = min(max(int(score), 0), 99)
        
        if score >= 80:
            rating = 'Excellent'
        elif score >= 60:
            rating = 'Good'
        elif score >= 40:
            rating = 'Fair'
        else:
            rating = 'Poor'

        return Response({
            'success': True,
            'data': {
                'score': score,
                'rating': rating,
                'metrics': {
                    'months_active': months_active,
                    'is_profitable_overall': total_income > total_expense
                }
            }
        })
