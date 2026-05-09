from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from app.auth.permissions.auth_token import BearerTokenAuthentication
from app.scrape.models.scrapeModel import Categories
from app.marketplace.models.category_settings import VendorCategorySetting
from app.auth.models.user import User
from app.marketplace.serializers.product_serializer import CategorySerializer
from app.marketplace.models.product import SubCategory
@api_view(['GET'])
@permission_classes([AllowAny])
def list_categories(request):
    """List categories visible to the user/vendor"""
    vendor_id = request.query_params.get('vendor_id')
    
    # Base categories (Admin created or no owner)
    base_categories = Categories.objects.filter(User_name__role=User.ADMIN) | Categories.objects.filter(User_name__isnull=True)
    
    if vendor_id:
        # Custom categories for this vendor
        custom = Categories.objects.filter(User_name_id=vendor_id)
        # Filter out disabled default categories
        disabled_ids = VendorCategorySetting.objects.filter(vendor_id=vendor_id, is_disabled=True).values_list('category_id', flat=True)
        base_categories = base_categories.exclude(id__in=disabled_ids)
        all_categories = base_categories | custom
    else:
        all_categories = base_categories

    serializer = CategorySerializer(all_categories, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def manage_category_visibility(request):
    """Vendors can disable default categories"""
    if request.user.role != User.VENDOR:
        return Response({'error': 'Only vendors can manage category visibility'}, status=status.HTTP_403_FORBIDDEN)
        
    category_id = request.data.get('category_id')
    is_disabled = request.data.get('is_disabled', True)
    
    category = Categories.objects.filter(id=category_id).first()
    if not category:
        return Response({'error': 'Category not found'}, status=404)
        
    # Ensure it's a default category (owned by Admin or none)
    if category.User_name and category.User_name.role != User.ADMIN:
        return Response({'error': 'Only default categories can be disabled'}, status=400)
        
    setting, created = VendorCategorySetting.objects.get_or_create(
        vendor=request.user, 
        category=category
    )
    setting.is_disabled = is_disabled
    setting.save()
    
    return Response({'message': f'Category visibility updated'})

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_custom_category(request):
    """Vendors or Admins can create categories"""
    if request.user.role not in [User.ADMIN, User.VENDOR]:
        return Response({'error': 'Only vendors or admins can create categories'}, status=403)
        
    name = request.data.get('name')
    if not name:
        return Response({'error': 'Name is required'}, status=400)
        
    category = Categories.objects.create(
        User_name=request.user,
        name=name
    )
    
    subcategories_data = request.data.get('subcategories', [])
    subs_created = []
    if subcategories_data and isinstance(subcategories_data, list):
        for item in subcategories_data:
            sub_name = item.get('name') if isinstance(item, dict) else item
            if sub_name and isinstance(sub_name, str):
                sub = SubCategory.objects.create(category=category, name=sub_name.strip())
                subs_created.append({'id': sub.id, 'name': sub.name})

    return Response({
        'id': category.id, 
        'name': category.name,
        'subcategories': subs_created
    }, status=201)

@api_view(['GET'])
@permission_classes([AllowAny])
def public_vendors_and_categories(request):
    """Returns all active vendors and visible categories for the public."""
    # Base categories (Admin created or no owner)
    base_categories = Categories.objects.filter(User_name__role=User.ADMIN) | Categories.objects.filter(User_name__isnull=True)
    categories_data = CategorySerializer(base_categories, many=True).data

    # Active vendors
    vendors = User.objects.filter(role=User.VENDOR, is_active=True).order_by('-date_joined')
    vendors_data = []
    for v in vendors:
        profile = getattr(v, 'vendor_profile', None)
        if profile and profile.is_approved:
            vendors_data.append({
                'id': v.id,
                'username': v.username,
                'brand_name': profile.brand_name,
                'logo': request.build_absolute_uri(profile.logo.url) if profile.logo else None
            })

    return Response({
        'categories': categories_data,
        'vendors': vendors_data
    })
