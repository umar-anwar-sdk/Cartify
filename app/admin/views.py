from django.shortcuts import render

def dashboard_view(request):
    """Serve the Admin Dashboard HTML template"""
    return render(request, 'admin/dashboard.html')

def login_view(request):
    """Serve the Admin Login HTML template"""
    return render(request, 'admin/login.html')
