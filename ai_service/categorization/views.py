"""
AI categorization views.
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import categorize_with_ai

class CategorizeTransactionView(APIView):
    """
    Accepts transaction data and recommends a category.
    
    POST /api/v1/categorize/
    {
       "description": "string",
       "amount": 100.0,
       "type": "expense",
       "business_id": "uuid"
    }
    """
    def post(self, request, *args, **kwargs):
        description = request.data.get('description')
        amount = request.data.get('amount')
        trans_type = request.data.get('type')
        business_id = request.data.get('business_id')

        if not all([description, business_id]):
            return Response(
                {"success": False, "message": "description and business_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        trans_type = trans_type or 'expense'
        amount = amount or 0.0
            
        category_data = categorize_with_ai(description, amount, trans_type, business_id)
        
        if not category_data:
            return Response(
                {"success": False, "message": "Could not categorize transaction."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        return Response({
            'success': True,
            'message': 'Categorized successfully',
            'data': {
                'category': category_data
            }
        }, status=status.HTTP_200_OK)
