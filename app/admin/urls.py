from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='admin_dashboard'),
    path('login/', views.login_view, name='admin_login'),
]
