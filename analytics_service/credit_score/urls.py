from django.urls import path
from .views import CreditScoreView

app_name = 'credit_score'
urlpatterns = [
    path('<uuid:business_id>/', CreditScoreView.as_view(), name='score'),
]
