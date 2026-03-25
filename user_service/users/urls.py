from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('token/refresh/', views.UserTokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
]
