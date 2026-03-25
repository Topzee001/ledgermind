"""Transaction URL patterns."""
from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.TransactionListCreateView.as_view(), name='list-create'),
    path('<uuid:pk>/', views.TransactionDetailView.as_view(), name='detail'),
    path('upload-csv/', views.TransactionCSVUploadView.as_view(), name='upload-csv'),
]
