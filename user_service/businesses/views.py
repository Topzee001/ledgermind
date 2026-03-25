"""
Business views.
"""
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Business
from .serializers import BusinessSerializer, BusinessListSerializer


class BusinessListCreateView(generics.ListCreateAPIView):
    """
    List all businesses for the authenticated user or create a new one.
    
    GET /api/v1/businesses/
    POST /api/v1/businesses/
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return BusinessListSerializer
        return BusinessSerializer

    def get_queryset(self):
        return Business.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BusinessSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        return Response({
            'success': True,
            'message': 'Business created successfully',
            'data': BusinessSerializer(business).data,
        }, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = BusinessListSerializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })


class BusinessDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a business.
    
    GET/PUT/PATCH/DELETE /api/v1/businesses/{id}/
    """
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Business.objects.filter(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'success': True,
            'message': 'Business updated successfully',
            'data': serializer.data,
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Business deleted successfully',
        }, status=status.HTTP_204_NO_CONTENT)
