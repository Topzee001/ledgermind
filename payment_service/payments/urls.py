"""Payment URL config."""
from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [
    path('', views.PaymentListView.as_view(), name='list'),
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate'),
    path('webhook/', views.InterswitchWebhookView.as_view(), name='webhook'),
]
