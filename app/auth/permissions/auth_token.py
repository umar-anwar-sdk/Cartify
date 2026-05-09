from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timezone
from django.utils import timezone as dtimezone
User = get_user_model()
SESSION_TOKEN_KEY = 'auth_token'

class BearerTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        token = None
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif 'token' in request.GET:
            token = request.GET.get('token')
            
        if not token:
            return None
        
        from django.contrib.sessions.models import Session
        
        for session in Session.objects.all():
            session_data = session.get_decoded()
            session_token_data = session_data.get(SESSION_TOKEN_KEY)
            if session_token_data and session_token_data.get('token') == token:
                expires_at = datetime.fromisoformat(session_token_data['expires_at'])
                if expires_at.replace(tzinfo=timezone.utc) < dtimezone.now():
                    raise AuthenticationFailed('Token expired')
                
                user = session_data.get('_auth_user_id')
                # Support legacy dict shape {'user_id': id} and the corrected primitive
                # shape where we store the raw id as a string/int.
                user_id = None
                if isinstance(user, dict):
                    user_id = user.get('user_id')
                else:
                    user_id = user

                if user_id is None:
                    continue

                try:
                    user_id_int = int(user_id)
                except Exception:
                    # invalid id stored; skip this session
                    continue

                try:
                    user = User.objects.get(id=user_id_int)
                    return (user, token)
                except User.DoesNotExist:
                    pass
        
