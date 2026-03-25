"""Category URL patterns."""
from django.urls import path
from . import views

app_name = 'categories'

urlpatterns = [
    path('', views.CategoryListCreateView.as_view(), name='list-create'),
]
