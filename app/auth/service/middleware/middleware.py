import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from ...models import PasswordResetOTP

User = get_user_model()

class UserExistenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path == '/api/auth/register/' and request.method == 'POST':
            try:
                data = json.loads(request.body)
                
                errors = {}
                
                required_fields = ['first_name', 'last_name', 'username', 'email', 'password']
                for field in required_fields:
                    if not data.get(field):
                        errors[field] = f'{field.replace("_", " ").title()} is required'
                        print(errors[field])
                
                password = data.get('password')
                if password and len(password) < 8:
                    errors['password'] = 'Password must be at least 8 characters'
                
                email = data.get('email')
                if email and '@' not in email:
                    errors['email'] = 'Invalid email format'
                
                if errors:
                    return JsonResponse({
                        'validation_error': True,
                        'errors': errors
                    }, status=400)
                
                username = data.get('username')
                
                if username and User.objects.filter(username=username).exists():
                    errors['username'] = 'Username already exists'
                
                if email and User.objects.filter(email=email).exists():
                    errors['email'] = 'Email already exists'
                
                if errors:
                    return JsonResponse({
                        'exists': True,
                        'errors': errors
                    }, status=400)
                    
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            except Exception as e:
                return JsonResponse({'error': 'Server error'}, status=500)
        
        
        
        if request.path == '/api/auth/login/' and request.method == 'POST':
            try:
                data = json.loads(request.body)
                username_or_email = data.get('username_or_email')
                password = data.get('password')
                
                errors = {}
                
                if not username_or_email:
                    errors['username_or_email'] = 'Username or email is required'
                if not password:
                    errors['password'] = 'Password is required'
                
                if errors:
                    return JsonResponse({
                        'validation_error': True,
                        'errors': errors
                    }, status=400)
                
                user = None
                if '@' in username_or_email:
                    try:
                        user = User.objects.get(email=username_or_email)
                    except User.DoesNotExist:
                        pass
                else:
                    try:
                        user = User.objects.get(username=username_or_email)
                    except User.DoesNotExist:
                        pass
                
                if not user:
                    return JsonResponse({
                        'error': 'User not found'
                    }, status=401)
                
                if not user.check_password(password):
                    return JsonResponse({
                        'error': 'Invalid password'
                    }, status=401)
                    
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            except Exception as e:
                return JsonResponse({'error': 'Server error'}, status=500)
        
        if request.path == '/api/auth/reset-password/' and request.method == 'POST':
            try:
                data = json.loads(request.body)
                email = data.get('email')
                
                if not email:
                    return JsonResponse({
                        'validation_error': True,
                        'errors': {'email': 'Email is required'}
                    }, status=400)
                
                if '@' not in email:
                    return JsonResponse({
                        'validation_error': True,
                        'errors': {'email': 'Invalid email format'}
                    }, status=400)
                    
                if not User.objects.filter(email=email).exists():
                    return JsonResponse({
                        'error': 'Email not found'
                    }, status=404)
                    
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            except Exception as e:
                return JsonResponse({'error': 'Server error'}, status=500)
        
        if request.path == '/api/auth/confirm-reset/' and request.method == 'POST':
            try:
                
                from django.utils import timezone
                from datetime import timedelta
                
                data = json.loads(request.body)
                
                otp = data.get('otp')
                new_password = data.get('new_password')
                email = data.get('email')
                errors = {}
                
                if not email:
                    errors['email'] = 'Email is required'
                if not otp:
                    errors['otp'] = 'OTP is required'
                if not new_password:
                    errors['new_password'] = 'New password is required'
                elif len(new_password) < 8:
                    errors['new_password'] = 'Password must be at least 8 characters'
                
                if errors:
                    return JsonResponse({
                        'validation_error': True,
                        'errors': errors
                    }, status=400)
                
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    return JsonResponse({
                        'error': 'Email not found'
                    }, status=404)
                
                otp_record = PasswordResetOTP.objects.filter(
                    user=user,
                    otp=otp,
                    is_used=False,
                    created_at__gte=timezone.now() - timedelta(minutes=10)
                ).first()
                
                if not otp_record:
                    return JsonResponse({
                        'error': 'Invalid or expired OTP'
                    }, status=400)
                    
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
        
        if request.path == '/api/auth/check-user/' and request.method == 'POST':
            try:
                data = json.loads(request.body)
                username = data.get('username')
                email = data.get('email')
                
                errors = {}
                
                if username and User.objects.filter(username=username).exists():
                    errors['username'] = 'Username already exists'
                
                if email and User.objects.filter(email=email).exists():
                    errors['email'] = 'Email already exists'
                
                return JsonResponse({
                    'exists': len(errors) > 0,
                    'errors': errors
                })
            except:
                return JsonResponse({'error': 'Invalid request'}, status=400)
        
        
    
        if request.path == '/api/auth/refresh-token/' and request.method == 'POST':
            data = json.loads(request.body)
            provided_refresh_token = data.get('refresh_token')
            if not provided_refresh_token:
                return JsonResponse({'error': 'Previous bearer token is required'}, status=400)
        
    
        return self.get_response(request)