from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import EmailTokenObtainPairView, MeView

urlpatterns = [
    path('auth/login/', EmailTokenObtainPairView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
]
