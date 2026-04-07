"""
AI categorization views.
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import categorize_with_ai, categorize_bulk_with_ai

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


class BulkCategorizeTransactionView(APIView):
    """
    Accepts a list of transactions to categorize at once.
    POST /api/v1/categorize/bulk/
    {
       "business_id": "uuid",
       "transactions": [
          {"description": "AWS monthly", "amount": 50.0, "type": "expense"},
          ...
       ]
    }
    """
    def post(self, request, *args, **kwargs):
        business_id = request.data.get('business_id')
        transactions = request.data.get('transactions', [])

        if not business_id or not isinstance(transactions, list):
            return Response(
                {"success": False, "message": "business_id and a list of transactions are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not transactions:
            return Response({'success': True, 'data': {'categories': []}})
            
        categorized_results = categorize_bulk_with_ai(transactions, business_id)
        
        return Response({
            'success': True,
            'message': f'Categorized {len(categorized_results)} transactions.',
            'data': {
                'categories': categorized_results
            }
        }, status=status.HTTP_200_OK)
