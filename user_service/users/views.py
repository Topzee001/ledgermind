"""
Views for the User Service.
"""
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user account.
    
    POST /api/v1/users/register/
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'success': True,
            'message': 'User registered successfully',
            'data': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_201_CREATED)


class UserLoginView(TokenObtainPairView):
    """
    Login and receive JWT tokens.
    
    POST /api/v1/users/login/
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token.
    
    POST /api/v1/users/token/refresh/
    """
    pass


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update the authenticated user's profile.
    
    GET/PUT/PATCH /api/v1/users/profile/
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(
            request.user, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': serializer.data,
        })


class HealthCheckView(APIView):
    """Health check endpoint."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'user-service',
        })
