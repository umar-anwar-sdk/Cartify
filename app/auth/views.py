import json
import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .permissions.auth_token import BearerTokenAuthentication
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import PasswordResetOTP
from .requestValidation import RegisterValidator, LoginValidator, ResetPasswordValidator, ConfirmResetValidator
from .service import EmailService
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from app.auth.permissions.auth_token import BearerTokenAuthentication

User = get_user_model()

SESSION_TOKEN_KEY = 'auth_token'
SESSION_REFRESH_TOKEN_EXPIRY_MINUTES = 1440 

def generate_token():
    return str(uuid.uuid4())



@csrf_exempt
def register(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Support both JSON and Multipart data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            files = {}
        else:
            data = request.POST.dict()
            files = request.FILES

        validator = RegisterValidator(data, files)
        if not validator.validate():
            return JsonResponse({'errors': validator.errors}, status=400)

        role = data.get('role', User.CUSTOMER).upper()
        if role not in [User.VENDOR, User.CUSTOMER]:
            return JsonResponse({'errors': {'role': 'Invalid role'}}, status=400)

        user = User.objects.create(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            password=make_password(data['password']),
            role=role,
            country=data.get('country'),
            state=data.get('state'),
            city=data.get('city'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        
        if role == User.VENDOR:
            from .models import VendorProfile
            # Vendors created by anonymous/self are NOT auto-approved
            is_approved = data.get('is_approved_by_admin', False)
            if isinstance(is_approved, str):
                is_approved = is_approved.lower() == 'true'
            
            VendorProfile.objects.create(
                user=user,
                brand_name=data['brand_name'],
                phone_number=data['phone_number'],
                email=data['email'],
                address=data['address'],
                logo=files.get('logo'),
                is_approved=is_approved
            )
        
        authenticated_user = authenticate(username=data['username'], password=data['password'])
        
        if authenticated_user:
            token = generate_token()
            request.session['_auth_user_id'] = str(authenticated_user.id)

            request.session[SESSION_TOKEN_KEY] = {
                'token': token,
                'expires_at': (timezone.now() + timedelta(minutes=SESSION_REFRESH_TOKEN_EXPIRY_MINUTES)).isoformat()
            }
            
            return JsonResponse({
                'message': 'User registered successfully',
                'user_id': authenticated_user.id,
                'token': token,
                'role': authenticated_user.role
            })
        else:
            return JsonResponse({'message': 'User registered but could not be authenticated'}, status=201)
    
    except Exception as e:
        logging.exception('Error in register view')
        return JsonResponse({'error': str(e)}, status=500)







@csrf_exempt
def guest_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        
        user, created = User.objects.get_or_create(
            device_id=device_id,
            defaults={
                'username': f'guest_{uuid.uuid4().hex[:10]}',
                'role': User.ANONYMOUS,
                'is_active': True,
                'country': data.get('country'),
                'state': data.get('state'),
                'city': data.get('city'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude')
            }
        )
        
        token = generate_token()
        # guest users are not authenticated via Django session (Anonymous), so we only
        # store our app token in session. Do not overwrite '_auth_user_id' here.
        request.session[SESSION_TOKEN_KEY] = {
            'token': token,
            'expires_at': (timezone.now() + timedelta(minutes=SESSION_REFRESH_TOKEN_EXPIRY_MINUTES)).isoformat()
        }
        
        # Show popup after 2 months (approx 60 days)
        show_popup = (timezone.now() - user.date_joined).days >= 60
        
        return JsonResponse({
            'message': 'Guest access granted',
            'token': token,
            'user_id': user.id,
            'role': user.role,
            'show_registration_popup': show_popup
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def convert_guest(request):
    """Migrate anonymous user to a full account"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)

        required_fields = ['username', 'email', 'first_name', 'last_name', 'password']
        field_errors = {}
        for field in required_fields:
            if not data.get(field):
                field_errors[field] = f'{field} is required to convert a guest account'

        if field_errors:
            return JsonResponse({'errors': field_errors}, status=400)

        if len(data.get('password', '')) < 8:
            field_errors['password'] = 'Password must be at least 8 characters'

        if field_errors:
            return JsonResponse({'errors': field_errors}, status=400)

        user = User.objects.filter(device_id=device_id, role=User.ANONYMOUS).first()
        if not user:
            return JsonResponse({'error': 'Guest account not found'}, status=404)

        # Check if username or email already exists for another user
        if User.objects.filter(username=data['username']).exclude(id=user.id).exists():
            return JsonResponse({'error': 'Username already taken'}, status=400)
        if User.objects.filter(email=data['email']).exclude(id=user.id).exists():
            return JsonResponse({'error': 'Email already registered'}, status=400)

        # Update user to full account
        user.username = data['username']
        user.email = data['email']
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.password = make_password(data['password'])
        user.role = User.CUSTOMER
        
        # Update location if provided
        if 'country' in data: user.country = data['country']
        if 'state' in data: user.state = data['state']
        if 'city' in data: user.city = data['city']
        if 'latitude' in data: user.latitude = data['latitude']
        if 'longitude' in data: user.longitude = data['longitude']
        
        user.save()

        # Migrate Favorites from device_id to this user
        from app.marketplace.models.product import Favorite
        Favorite.objects.filter(device_id=device_id).update(user=user, device_id=None)
        
        user.save()
        
        return JsonResponse({
            'message': 'Account converted successfully',
            'user_id': user.id,
            'role': user.role
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def signin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        validator = LoginValidator(data)
        
        if not validator.validate():
            return JsonResponse({'errors': validator.errors}, status=400)
        
        username_or_email = data['username_or_email']
        password = data['password']
        user = None
        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
                username = user.username if user else None
                userid=user.id
            except User.DoesNotExist:
                username = None
                userid=None
        else:
            username = username_or_email
        
        user = authenticate(username=username, password=password)
        userid=user.id
        if user:
            token = generate_token()

            # Correctly store the user id (string) in session so Django can parse it later.
            request.session['_auth_user_id'] = str(userid)

            request.session[SESSION_TOKEN_KEY] = {
                'token': token,
                'expires_at': (timezone.now() + timedelta(minutes=SESSION_REFRESH_TOKEN_EXPIRY_MINUTES)).isoformat()
            }
            
            
            return JsonResponse({
                'message': 'Login successful',
                'token': token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'country': user.country,
                    'state': user.state,
                    'city': user.city,
                    'latitude': user.latitude,
                    'longitude': user.longitude,
                }
            })
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def refresh_token(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        provided_refresh_token = data.get('refresh_token')
      
        session_refresh_token = request.session.get(SESSION_TOKEN_KEY)
        
        if not session_refresh_token:
            return JsonResponse({'error': 'Invalid refresh token found'}, status=401)
        
        
        refresh_token_data = session_refresh_token
        expires_at = timezone.datetime.fromisoformat(refresh_token_data['expires_at'])
        
        if refresh_token_data['token'] != provided_refresh_token:
            return JsonResponse({'error': 'Invalid refresh token'}, status=401)
        
        if expires_at < timezone.now():
            return JsonResponse({'error': 'Refresh token expired'}, status=401)
        
        new_token = generate_token()
       
        request.session[SESSION_TOKEN_KEY] = {
            'token': new_token,
            'expires_at': (timezone.now() + timedelta(minutes=SESSION_REFRESH_TOKEN_EXPIRY_MINUTES)).isoformat()
        }
        
   
        return JsonResponse({
            'message': 'Token refreshed successfully',
            'token': new_token,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




@csrf_exempt
def reset_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        validator = ResetPasswordValidator(data)
        
        if not validator.validate():
            return JsonResponse({'errors': validator.errors}, status=400)
        
        user = User.objects.get(email=data['email'])
        email_service = EmailService()
        otp = email_service.generate_otp()
        
       
        PasswordResetOTP.objects.filter(
            user=user, 
            is_used=False
        ).update(is_used=True)
        
        PasswordResetOTP.objects.create(
            user=user,
            otp=otp
        )
        
        if email_service.send_reset_otp(user.email, otp):
            return JsonResponse({'message': 'OTP sent to your email', 'email': data['email']})
        else:
            return JsonResponse({'error': 'Failed to send email'}, status=500)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def confirm_reset(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        validator = ConfirmResetValidator(data)
        
        if not validator.validate():
            return JsonResponse({'errors': validator.errors}, status=400)
        
        user = User.objects.get(email=data['email'])
        
        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            otp=data['otp'],
            is_used=False,
            created_at__gte=timezone.now() - timedelta(minutes=10)
        ).first()
        
        if not otp_record:
            return JsonResponse({'error': 'Invalid or expired OTP'}, status=400)
        
        user.password = make_password(data['new_password'])
        user.save()
        
        otp_record.is_used = True
        otp_record.save()
        
        if SESSION_TOKEN_KEY in request.session:
            del request.session[SESSION_TOKEN_KEY]
        
        return JsonResponse({'message': 'Password reset successfully'})
    
    except Exception as e:
        return JsonResponse({'errors...': str(e)}, status=500)
    
    

@csrf_exempt
def check_user(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
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
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_profile(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        
        user = request.user 
        
        allowed_fields = [
            'first_name', 
            'last_name', 
            'email',
            'username',
            'country',
            'state',
            'city',
            'latitude',
            'longitude'
        ]

        if 'username' in data and data['username'] != user.username:
            if User.objects.filter(username=data['username']).exists():
                return JsonResponse({'error': 'Username already used Try another username'}, status=400)
        
        if 'email' in data and data['email'] != user.email:
            if User.objects.filter(email=data['email']).exists():
                return JsonResponse({'error': 'Email already used Try another email'}, status=400)

        updated_fields = {}
        for key, value in data.items():
            if key in allowed_fields:
                current_value = getattr(user, key)
                if current_value != value:
                    setattr(user, key, value)
                    updated_fields[key] = value

        if updated_fields:
            user.save()
            message = 'Profile updated successfully'
        else:
            message = 'No changes detected or fields were not allowed to be updated.'

        response_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'country': user.country,
            'state': user.state,
            'city': user.city,
            'latitude': user.latitude,
            'longitude': user.longitude,
        }
        
        return JsonResponse({
            'message': message,
            'user': response_data
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format in request body'}, status=400)
    
    except Exception as e:
        print(f"Error during profile update: {e}")
        return JsonResponse({'error': f'An internal error occurred during the update {e}'}, status=500)



@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        user = request.user
        response_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'country': user.country,
            'state': user.state,
            'city': user.city,
            'latitude': user.latitude,
            'longitude': user.longitude,
        }
        
        return JsonResponse({'user': response_data})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def public_config(request):
    """Public settings for frontend (Platform Name, Popup Logic)"""
    from .admin_views import _load_system_settings, _load_popup_settings
    
    sys = _load_system_settings()
    pop = _load_popup_settings()
    
    return Response({
        'platform_name': sys.get('platform_name', 'Cartify'),
        'popup': {
            'enabled': pop.get('enabled', True),
            'delay_days': pop.get('popup_delay_days', 60),
            'message': pop.get('message', ''),
            'cta_text': pop.get('cta_text', 'Sign Up Now'),
        }
    })