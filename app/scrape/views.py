import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models.scrapeModel import ScrapedProduct, Categories ,productClick
from .requestValidation import ScrapeValidator
from .service import ScraperService
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from app.auth.permissions.auth_token import BearerTokenAuthentication
from app.auth.models.user import User

def click_count_incrementer(user, product, click_type):
    # Handle anonymous users
    db_user = user if user.is_authenticated else None
    
    click_record, created = productClick.objects.get_or_create(
        User_name=db_user,
        product=product
    )
    
    if click_type == 'scrape':
        click_record.scrape_click_count = (click_record.scrape_click_count or 0) + 1
    elif click_type == 'web':
        click_record.web_click_count = (click_record.web_click_count or 0) + 1
    
    click_record.save()
    return click_record

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([AllowAny])
def scrape_product(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        validator = ScrapeValidator(data)
        
        if not validator.validate():
            return JsonResponse({'errors': validator.errors}, status=400)
        
        url = data['url']
        scraper = ScraperService()
        product_data = scraper.scrape_product_data(url)
        
        sitename=product_data.get('site_name')
        
        # Handle anonymous/guest user logic
        user = request.user if request.user.is_authenticated else None
        device_id = data.get('device_id')
        
        if not user and device_id:
            # Mirror guest_login logic to find or create the guest user
            user, created = User.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'username': f'guest_{uuid.uuid4().hex[:10]}',
                    'role': User.ANONYMOUS,
                    'is_active': True
                }
            )
        
        category, _ = Categories.objects.get_or_create(User_name=user, name=sitename)
        
        scraped_product, created = ScrapedProduct.objects.update_or_create(
            User_name=user,
            url=url,
            defaults={
                'title': product_data.get('title', ''),
                'price': product_data.get('price', ''),
                'images': product_data.get('images', []),
                'description': product_data.get('description', ''),
                'category': category
            }
        )
        
        click_count_incrementer(request.user, scraped_product, 'scrape')
                
        return JsonResponse({
            'message': f'Product {"created" if created else "updated"} successfully',
            'data': {
                'id': scraped_product.id,
                'user_id': scraped_product.User_name.id if scraped_product.User_name else None,
                'url': scraped_product.url,
                'title': scraped_product.title,
                'price': scraped_product.price,
                'images': scraped_product.images,
                'description': scraped_product.description,
                'scraped_at': scraped_product.scraped_at
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET', 'POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([AllowAny])
def get_all_categories(request):
    try:
        user = request.user if request.user.is_authenticated else None
        
        # Support device_id for anonymous category retrieval
        if not user and request.method == 'POST':
            try:
                data = json.loads(request.body)
                device_id = data.get('device_id')
                if device_id:
                    user = User.objects.filter(device_id=device_id).first()
            except Exception:
                pass
                
        categories = Categories.objects.filter(User_name=user).values('id', 'name')
        return JsonResponse({'categories': list(categories)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([AllowAny])
def get_products_by_category(request):
    try:
        data = json.loads(request.body)
        category_name = data.get('category')
        if not category_name:
            return JsonResponse({'error': 'Category name is required'}, status=400)
        
        user = request.user if request.user.is_authenticated else None
        
        # Support device_id for anonymous product retrieval
        if not user:
            device_id = data.get('device_id')
            if device_id:
                user = User.objects.filter(device_id=device_id).first()
                
        try:
            category = Categories.objects.get(User_name=user, name=category_name)
        except Categories.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=404)
        
        products = ScrapedProduct.objects.filter(User_name=user, category=category).values(
            'id', 'url', 'title', 'price', 'images', 'description', 'scraped_at'
        )
        return JsonResponse({
            'category': category_name,
            'products': list(products)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET', 'POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([AllowAny])
def get_product_by_id(request, product_id):
    try:
        user = request.user if request.user.is_authenticated else None
        
        # Support device_id for anonymous product retrieval
        if not user and request.method == 'POST':
            try:
                data = json.loads(request.body)
                device_id = data.get('device_id')
                if device_id:
                    user = User.objects.filter(device_id=device_id).first()
            except Exception:
                pass
                
        product = ScrapedProduct.objects.get(User_name=user, id=product_id)
        click_count_incrementer(request.user, product, 'web')
        return JsonResponse({
            'product': {
                'id': product.id,
                'url': product.url,
                'title': product.title,
                'price': product.price,
                'images': product.images,
                'description': product.description,
                'category': product.category.name if product.category else None,
                'scraped_at': product.scraped_at
            }
        })
    except ScrapedProduct.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([AllowAny])
def get_count_to_check_clicks(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        if not product_id:
            return JsonResponse({'error': 'Product ID is required'}, status=400)
        
        user = request.user if request.user.is_authenticated else None
        product = ScrapedProduct.objects.get(id=product_id)
        count = productClick.objects.filter(User_name=user, product=product).first()
        
        if count:
            return JsonResponse({
                'scrape_click_count': count.scrape_click_count or 0,
                'web_view_click_count': count.web_click_count or 0
            })
        else:
            return JsonResponse({'scrape_click_count': 0, 'web_click_count': 0})
    except ScrapedProduct.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_list_all_scraped_items(request):
    """Admin view to see all scraped items from all users"""
    if not (request.user.role == User.ADMIN or request.user.is_staff):
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        products = ScrapedProduct.objects.all().select_related('User_name', 'category')
        data = []
        for p in products:
            data.append({
                'id': p.id,
                'user': p.User_name.username if p.User_name else 'System',
                'url': p.url,
                'title': p.title,
                'price': p.price,
                'category': p.category.name if p.category else None,
                'scraped_at': p.scraped_at
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
