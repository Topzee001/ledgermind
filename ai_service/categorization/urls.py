"""Categorization URL patterns."""
from django.urls import path
from . import views

app_name = 'categorization'

urlpatterns = [
    path('', views.CategorizeTransactionView.as_view(), name='categorize'),
    path('bulk/', views.BulkCategorizeTransactionView.as_view(), name='bulk-categorize'),
]
