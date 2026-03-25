"""
Transaction views.
"""
import csv
import io
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction

from .models import Transaction
from categories.models import Category
from .serializers import TransactionSerializer, TransactionUploadSerializer
from .services import categorize_transaction_via_ai


class TransactionListCreateView(generics.ListCreateAPIView):
    """
    List all transactions for a business or create a new one.
    
    GET /api/v1/transactions/?business_id=uuid
    POST /api/v1/transactions/
    """
    serializer_class = TransactionSerializer

    def get_queryset(self):
        business_id = self.request.query_params.get('business_id')
        queryset = Transaction.objects.all()
        if business_id:
            queryset = queryset.filter(business_id=business_id)
            
        type_filter = self.request.query_params.get('type')
        if type_filter in ['income', 'expense']:
            queryset = queryset.filter(type=type_filter)
            
        return queryset

    def create(self, request, *args, **kwargs):
        business_id = request.data.get('business_id')
        if not business_id:
            return Response(
                {"success": False, "message": "business_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Determine if we should trigger AI category
        category_id = serializer.validated_data.get('category')
        description = serializer.validated_data.get('description', '')
        amount = serializer.validated_data.get('amount')
        trans_type = serializer.validated_data.get('type')
        
        ai_categorized = False
        
        # If no category is given, ask AI
        if not category_id and description:
            ai_category_data = categorize_transaction_via_ai(description, amount, trans_type, business_id)
            if ai_category_data and ai_category_data.get('id'):
                try:
                    cat = Category.objects.get(id=ai_category_data['id'])
                    serializer.validated_data['category'] = cat
                    ai_categorized = True
                except Category.DoesNotExist:
                    pass
        
        transaction_instance = serializer.save(ai_categorized=ai_categorized)
        
        return Response({
            'success': True,
            'message': 'Transaction created successfully',
            'data': TransactionSerializer(transaction_instance).data,
        }, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            res = self.get_paginated_response(serializer.data)
            res.data['success'] = True
            return res
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a transaction.
    """
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # If user updates category manually, ai_categorized is false
        if 'category' in serializer.validated_data and serializer.validated_data['category'] != instance.category:
            serializer.validated_data['ai_categorized'] = False
            
        serializer.save()
        return Response({
            'success': True,
            'message': 'Transaction updated successfully',
            'data': serializer.data,
        })
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Transaction deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class TransactionCSVUploadView(generics.GenericAPIView):
    """
    Upload CSV for bulk transaction import.
    """
    serializer_class = TransactionUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        business_id = serializer.validated_data['business_id']
        file = serializer.validated_data['file']
        
        if not file.name.endswith('.csv'):
            return Response({'success': False, 'message': 'Only CSV files are allowed'}, status=status.HTTP_400_BAD_REQUEST)

        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        transactions_to_create = []
        errors = []
        
        for idx, row in enumerate(reader, start=2):
            try:
                # Expecting type, amount, date, description
                type_val = row.get('type', 'expense').lower()
                amount_val = float(row.get('amount', 0))
                date_val = row.get('date')
                desc_val = row.get('description', '')
                
                if not date_val:
                    errors.append(f"Row {idx}: Missing date")
                    continue
                    
                t = Transaction(
                    business_id=business_id,
                    type=type_val,
                    amount=amount_val,
                    date=date_val,
                    description=desc_val,
                    source='csv'
                )
                transactions_to_create.append(t)
            except Exception as e:
                errors.append(f"Row {idx}: Data error - {str(e)}")
                
        if transactions_to_create:
            with transaction.atomic():
                Transaction.objects.bulk_create(transactions_to_create)
                
        return Response({
            'success': True,
            'message': f'Imported {len(transactions_to_create)} transactions. {len(errors)} errors.',
            'errors': errors
        }, status=status.HTTP_201_CREATED if transactions_to_create else status.HTTP_400_BAD_REQUEST)
