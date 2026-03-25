"""AI Service URL configuration."""
from django.urls import path, include
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'status': 'healthy', 'service': 'ai-service'})

urlpatterns = [
    path('api/v1/categorize/', include('categorization.urls')),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
