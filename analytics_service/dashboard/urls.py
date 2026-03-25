from django.urls import path
from .views import DashboardDataView

app_name = 'dashboard'
urlpatterns = [
    path('<uuid:business_id>/', DashboardDataView.as_view(), name='dashboard-data'),
]
