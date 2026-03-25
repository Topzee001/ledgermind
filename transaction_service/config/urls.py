"""Transaction Service URL configuration."""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'status': 'healthy', 'service': 'transaction-service'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/transactions/', include('transactions.urls')),
    path('api/v1/categories/', include('categories.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
