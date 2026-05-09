from django.http import JsonResponse
from django.contrib.auth import get_user_model
from ...models.token import Token

User = get_user_model()

class BearerTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = [
            '/api/auth/register/',
            '/api/auth/login/',
            '/admin/',
            
            
              
        ]
    
    def __call__(self, request):
        if any(request.path.startswith(path) for path in self.public_paths):
            return self.get_response(request)
                
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return JsonResponse({
                'error': 'Authorization bearer token is required'
            }, status=401)
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Invalid authorization header format. Use: Bearer <token>'
            }, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            token_obj = Token.objects.select_related('user').get(key=token)
            request.user = token_obj.user
        except Token.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid token'
            }, status=401)
        
        return self.get_response(request)