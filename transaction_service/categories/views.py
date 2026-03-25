"""Category API views."""
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response

from .models import Category
from .serializers import CategorySerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    """
    List all categories (default ones + business specific)
    or create a new custom business category.
    
    GET /api/v1/categories/?business_id=uuid
    POST /api/v1/categories/
    """
    serializer_class = CategorySerializer

    def get_queryset(self):
        business_id = self.request.query_params.get('business_id') or self.request.data.get('business_id')
        
        # Include default system categories
        query = Q(is_default=True)
        
        # If business_id is provided, also include custom categories for this business
        if business_id:
            query |= Q(business_id=business_id)
            
        return Category.objects.filter(query)

    def create(self, request, *args, **kwargs):
        business_id = request.data.get('business_id')
        if not business_id:
            return Response(
                {"success": False, "message": "business_id is required to create a category."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Force custom category to not be default
        data = request.data.copy()
        data['is_default'] = False
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Category created successfully',
            'data': CategorySerializer(category).data,
        }, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })
