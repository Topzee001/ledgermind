from django.urls import path
from .views import CashflowForecastView

app_name = 'forecasting'
urlpatterns = [
    path('cashflow/<uuid:business_id>/', CashflowForecastView.as_view(), name='forecast-cashflow'),
]
