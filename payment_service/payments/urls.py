"""Payment URL config."""
from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [
    path('', views.PaymentListView.as_view(), name='list'),
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate'),
    path('authenticate-otp/', views.AuthenticateOTPView.as_view(), name='authenticate_otp'),
    path('verify/', views.VerifyPaymentView.as_view(), name='verify'),
    path('webhook/', views.InterswitchWebhookView.as_view(), name='webhook'),
]
