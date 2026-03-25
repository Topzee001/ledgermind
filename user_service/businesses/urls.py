"""Business URL patterns."""
from django.urls import path
from . import views

app_name = 'businesses'

urlpatterns = [
    path('', views.BusinessListCreateView.as_view(), name='list-create'),
    path('<uuid:pk>/', views.BusinessDetailView.as_view(), name='detail'),
]
