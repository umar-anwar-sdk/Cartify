import csv
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from app.auth.permissions.auth_token import BearerTokenAuthentication
from app.auth.models.user import User
from app.auth.models.vendor import VendorProfile
from app.marketplace.models.product import Product, Favorite, SubCategory
from app.marketplace.serializers.product_serializer import ProductSerializer, CategorySerializer
from app.scrape.models.scrapeModel import Categories


def is_admin(user):
    return user.role == User.ADMIN or user.is_staff


# ─── Vendors ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def list_vendors(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendors = User.objects.filter(role=User.VENDOR).order_by('-date_joined')
    data = []
    for v in vendors:
        profile = getattr(v, 'vendor_profile', None)
        product_count = Product.objects.filter(vendor=v).count()
        data.append({
            'id': v.id,
            'username': v.username,
            'email': v.email,
            'brand_name': profile.brand_name if profile else None,
            'phone': profile.phone_number if profile else None,
            'is_approved': profile.is_approved if profile else False,
            'kyc_status': profile.kyc_status if profile else 'PENDING',
            'rejection_reason': profile.rejection_reason if profile else None,
            'is_active': v.is_active,
            'product_count': product_count,
            'created_at': v.date_joined.isoformat(),
            'kyc_details': {
                'phone': profile.phone_number if profile else None,
                'address': profile.address if profile else None,
            } if profile else None,
        })
    return Response(data)


@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_vendor_detail(request, vendor_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    profile = getattr(vendor, 'vendor_profile', None)
    logo_url = None
    if profile and profile.logo:
        try:
            logo_url = request.build_absolute_uri(profile.logo.url)
        except Exception:
            logo_url = None
    product_count = Product.objects.filter(vendor=vendor).count()
    categories_created = Categories.objects.filter(User_name=vendor).count()
    return Response({
        'id': vendor.id,
        'username': vendor.username,
        'email': vendor.email,
        'is_active': vendor.is_active,
        'brand_name': profile.brand_name if profile else None,
        'is_approved': profile.is_approved if profile else False,
        'kyc_status': profile.kyc_status if profile else 'PENDING',
        'rejection_reason': profile.rejection_reason if profile else None,
        'product_count': product_count,
        'categories_created': categories_created,
        'kyc': {
            'phone': profile.phone_number if profile else None,
            'address': profile.address if profile else None,
            'email': profile.email if profile else None,
            'logo': logo_url,
            'created_at': profile.created_at.isoformat() if profile else None,
        }
    })


@api_view(['PATCH'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_edit_vendor(request, vendor_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    profile = getattr(vendor, 'vendor_profile', None)
    data = request.data

    # Update user fields
    for field in ['email', 'first_name', 'last_name']:
        if field in data:
            setattr(vendor, field, data[field])
    if 'password' in data and data['password']:
        vendor.password = make_password(data['password'])
    vendor.save()

    # Update profile fields
    if profile:
        for field in ['brand_name', 'phone_number', 'address']:
            if field in data:
                setattr(profile, field, data[field])
        profile.save()

    return Response({'message': 'Vendor updated successfully'})


@api_view(['DELETE'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_delete_vendor(request, vendor_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    vendor.delete()
    return Response({'message': 'Vendor deleted successfully'})


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def approve_vendor(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    
    vendor_id = request.data.get('vendor_id')
    status_req = request.data.get('status')  # 'APPROVED' or 'REJECTED'
    reason = request.data.get('reason', '')

    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    
    profile = getattr(vendor, 'vendor_profile', None)
    if not profile:
        return Response({'error': 'Vendor profile missing'}, status=400)

    if status_req not in ['APPROVED', 'REJECTED']:
        return Response({'error': "Status must be either 'APPROVED' or 'REJECTED'"}, status=400)

    if status_req == 'APPROVED':
        profile.kyc_status = VendorProfile.KYC_APPROVED
        profile.is_approved = True
        vendor.is_active = True
    else:
        profile.kyc_status = VendorProfile.KYC_REJECTED
        profile.is_approved = False
        profile.rejection_reason = reason
        vendor.is_active = False
    
    profile.save()
    vendor.save()
    
    return Response({
        'message': f'Vendor {status_req.lower()}',
        'kyc_status': profile.kyc_status,
        'is_active': vendor.is_active
    })


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def toggle_vendor_active(request, vendor_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    vendor.is_active = not vendor.is_active
    vendor.save()
    return Response({'message': f'Vendor {"activated" if vendor.is_active else "deactivated"}', 'is_active': vendor.is_active})


# ─── Products ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_list_products(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendor_id = request.query_params.get('vendor_id')
    products = Product.objects.all().order_by('-created_at')
    if vendor_id:
        products = products.filter(vendor_id=vendor_id)
    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['DELETE'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_delete_product(request, product_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    product = Product.objects.filter(id=product_id).first()
    if not product:
        return Response({'error': 'Product not found'}, status=404)
    product.delete()
    return Response({'message': 'Product deleted successfully'})


@api_view(['PATCH'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_edit_product(request, product_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    product = Product.objects.filter(id=product_id).first()
    if not product:
        return Response({'error': 'Product not found'}, status=404)
    data = request.data
    for field in ['name', 'description', 'price', 'original_price', 'discount', 'is_active', 'category', 'subcategory']:
        if field in data:
            setattr(product, field, data[field])
    try:
        product.full_clean()
    except ValidationError as e:
        return Response({'error': e.message_dict if hasattr(e, 'message_dict') else e.messages}, status=400)
    product.save()
    return Response(ProductSerializer(product, context={'request': request}).data)


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_toggle_product(request, product_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    product = Product.objects.filter(id=product_id).first()
    if not product:
        return Response({'error': 'Product not found'}, status=404)
    product.is_active = not product.is_active
    product.save()
    return Response({'message': f'Product {"shown" if product.is_active else "hidden"}', 'is_active': product.is_active})


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_post_product(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    vendor_id = request.data.get('vendor_id')
    if not vendor_id:
        return Response({'error': 'Vendor ID is required'}, status=400)
    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    serializer = ProductSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(vendor=vendor)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_create_vendor(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    data = request.data
    required = ['username', 'email', 'first_name', 'last_name', 'password', 'brand_name', 'phone_number', 'address']
    errors = {}
    for field in required:
        if not data.get(field):
            errors[field] = f"{field} is required"
    if errors:
        return Response({'errors': errors}, status=400)
    try:
        user = User.objects.create(
            username=data.get('username'),
            email=data.get('email'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            password=make_password(data.get('password')),
            role=User.VENDOR,
            country=data.get('country'),
            state=data.get('state'),
            city=data.get('city'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        VendorProfile.objects.create(
            user=user,
            brand_name=data.get('brand_name'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            address=data.get('address'),
            logo=request.FILES.get('logo'),
            is_approved=True
        )
        return Response({'message': 'Vendor created and approved', 'user_id': user.id}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# ─── Categories ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_list_categories(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    categories = Categories.objects.filter(
        Q(User_name__role=User.ADMIN) | Q(User_name__isnull=True)
    ).order_by('id')
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_create_category(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
        
    name = request.data.get('name')
    if not name:
        return Response({'error': 'Category name is required'}, status=400)
        
    category = Categories.objects.create(User_name=request.user, name=name)
    
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

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_create_subcategory(request, category_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    category = Categories.objects.filter(id=category_id).first()
    if not category:
        return Response({'error': 'Category not found'}, status=404)
    name = request.data.get('name')
    if not name:
        return Response({'error': 'Subcategory name is required'}, status=400)
    sub = SubCategory.objects.create(category=category, name=name)
    return Response({'id': sub.id, 'name': sub.name, 'category_id': category.id}, status=201)


@api_view(['PATCH'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_edit_subcategory(request, subcategory_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    sub = SubCategory.objects.filter(id=subcategory_id).first()
    if not sub:
        return Response({'error': 'Subcategory not found'}, status=404)
    if 'name' in request.data:
        sub.name = request.data['name']
    if 'category' in request.data:
        new_category = Categories.objects.filter(id=request.data['category']).first()
        if not new_category:
            return Response({'error': 'Target category not found'}, status=404)
        sub.category = new_category
    sub.save()
    return Response({'id': sub.id, 'name': sub.name, 'category_id': sub.category_id})


@api_view(['DELETE'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_delete_subcategory(request, subcategory_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    sub = SubCategory.objects.filter(id=subcategory_id).first()
    if not sub:
        return Response({'error': 'Subcategory not found'}, status=404)
    sub.delete()
    return Response({'message': 'Subcategory deleted'})


@api_view(['PATCH'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_edit_category(request, category_id):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    category = Categories.objects.filter(id=category_id).first()
    if not category:
        return Response({'error': 'Category not found'}, status=404)
    if 'name' in request.data:
        category.name = request.data['name']
    if hasattr(category, 'is_active') and 'is_active' in request.data:
        category.is_active = request.data['is_active']
    category.save()
    
    # Handle inline subcategories sync
    if 'subcategories' in request.data:
        subcategories_data = request.data['subcategories']
        if isinstance(subcategories_data, list):
            existing_subs = {sub.id: sub for sub in category.subcategories.all()}
            processed_ids = []
            
            for item in subcategories_data:
                if isinstance(item, dict):
                    sub_id = item.get('id')
                    sub_name = item.get('name')
                    if not sub_name: continue
                    
                    if sub_id and sub_id in existing_subs:
                        sub = existing_subs[sub_id]
                        sub.name = sub_name.strip()
                        sub.save()
                        processed_ids.append(sub.id)
                    else:
                        sub = SubCategory.objects.create(category=category, name=sub_name.strip())
                        processed_ids.append(sub.id)
                elif isinstance(item, str):
                    sub = SubCategory.objects.create(category=category, name=item.strip())
                    processed_ids.append(sub.id)
            
    # Serialize the updated category
    serializer = CategorySerializer(category)
    return Response(serializer.data)


@api_view(['DELETE'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_delete_category(request, category_id):

    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    category = Categories.objects.filter(id=category_id).first()
    if not category:
        return Response({'error': 'Category not found'}, status=404)
    category.delete()
    return Response({'message': 'Category deleted'})


@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_toggle_category(request, category_id):

    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    category = Categories.objects.filter(id=category_id).first()
    if not category:
        return Response({'error': 'Category not found'}, status=404)
    if hasattr(category, 'is_active'):
        category.is_active = not category.is_active
        category.save()
        return Response({'is_active': category.is_active})
    return Response({'message': 'Toggle not supported on this model'}, status=400)


# ─── Favorites Monitoring ─────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_favorites(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    products = Product.objects.annotate(
        fav_count=Count('favorited_by'),
        unique_users=Count('favorited_by__user', distinct=True)
    ).filter(fav_count__gt=0).order_by('-fav_count')[:50]
    data = []
    for p in products:
        profile = getattr(p.vendor, 'vendor_profile', None)
        data.append({
            'id': p.id,
            'name': p.name,
            'vendor_name': profile.brand_name if profile else p.vendor.username,
            'favorites_count': p.fav_count,
            'unique_users_count': p.unique_users,
            'price': str(p.price),
            'original_price': str(p.original_price) if p.original_price else None,
            'image': request.build_absolute_uri(p.image.url) if p.image else None,
        })
    return Response(data)

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_list_customers(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    customers = User.objects.filter(role=User.CUSTOMER).order_by('-date_joined')
    data = []
    for u in customers:
        data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'date_joined': u.date_joined,
            'is_active': u.is_active,
            'favorites_count': Favorite.objects.filter(user=u).count()
        })
    return Response(data)

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_list_guests(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)
    guests = User.objects.filter(role=User.ANONYMOUS).order_by('-date_joined')
    data = []
    for u in guests:
        data.append({
            'id': u.id,
            'device_id': u.device_id,
            'first_visit': u.date_joined,
            'last_active': u.last_login,
            'favorites_count': Favorite.objects.filter(device_id=u.device_id).count() if u.device_id else 0
        })
    return Response(data)

# ─── Analytics ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)

    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    last_30 = now - timedelta(days=30)
    last_7 = now - timedelta(days=7)

    total_vendors = User.objects.filter(role=User.VENDOR).count()
    active_vendors = User.objects.filter(role=User.VENDOR, is_active=True).count()
    pending_kyc = VendorProfile.objects.filter(is_approved=False).count()
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    total_customers = User.objects.filter(role=User.CUSTOMER).count()
    total_guests = User.objects.filter(role=User.ANONYMOUS).count()
    total_categories = Categories.objects.filter(
        Q(User_name__role=User.ADMIN) | Q(User_name__isnull=True)
    ).count()
    total_favorites = Favorite.objects.count()

    # Monthly vendor signups (last 6 months)
    vendor_growth = []
    for i in range(5, -1, -1):
        month_start = (now - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        count = User.objects.filter(role=User.VENDOR, date_joined__gte=month_start, date_joined__lt=month_end).count()
        vendor_growth.append({'month': month_start.strftime('%b %Y'), 'count': count})

    # Daily product posts (last 7 days)
    product_posts = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        count = Product.objects.filter(created_at__date=day).count()
        product_posts.append({'day': day.strftime('%a'), 'count': count})

    # User growth (last 6 months)
    user_growth = []
    for i in range(5, -1, -1):
        month_start = (now - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        customers = User.objects.filter(role=User.CUSTOMER, date_joined__gte=month_start, date_joined__lt=month_end).count()
        guests = User.objects.filter(role=User.ANONYMOUS, date_joined__gte=month_start, date_joined__lt=month_end).count()
        user_growth.append({'month': month_start.strftime('%b %Y'), 'customers': customers, 'guests': guests})

    # Top vendors by product count
    top_vendors = []
    for v in User.objects.filter(role=User.VENDOR, is_active=True):
        pc = Product.objects.filter(vendor=v).count()
        fc = Favorite.objects.filter(product__vendor=v).count()
        if pc > 0:
            profile = getattr(v, 'vendor_profile', None)
            top_vendors.append({'name': profile.brand_name if profile else v.username, 'products': pc, 'favorites': fc})
    top_vendors = sorted(top_vendors, key=lambda x: x['favorites'], reverse=True)[:5]

    # Guest conversion rate
    converted = User.objects.filter(role=User.CUSTOMER, device_id__isnull=False).count()
    conversion_rate = round((converted / total_guests * 100), 1) if total_guests > 0 else 0

    return Response({
        'stats': {
            'total_vendors': total_vendors,
            'active_vendors': active_vendors,
            'pending_kyc': pending_kyc,
            'total_products': total_products,
            'active_products': active_products,
            'total_customers': total_customers,
            'total_guests': total_guests,
            'total_categories': total_categories,
            'total_favorites': total_favorites,
            'conversion_rate': conversion_rate,
        },
        'vendor_growth': vendor_growth,
        'product_posts': product_posts,
        'user_growth': user_growth,
        'top_vendors': top_vendors,
    })


# ─── CSV Export ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def admin_export_csv(request, report_type):
    if not is_admin(request.user):
        return Response({'error': 'Admin access required'}, status=403)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    writer = csv.writer(response)

    if report_type == 'vendors':
        writer.writerow(['ID', 'Brand Name', 'Email', 'Phone', 'Status', 'KYC', 'Products', 'Joined'])
        for v in User.objects.filter(role=User.VENDOR):
            profile = getattr(v, 'vendor_profile', None)
            writer.writerow([
                v.id, profile.brand_name if profile else '', v.email,
                profile.phone_number if profile else '',
                'Active' if v.is_active else 'Inactive',
                'Approved' if (profile and profile.is_approved) else 'Pending',
                Product.objects.filter(vendor=v).count(),
                v.date_joined.strftime('%Y-%m-%d'),
            ])

    elif report_type == 'products':
        writer.writerow(['ID', 'Name', 'Vendor', 'Category', 'Original Price', 'Discounted Price', 'Discount %', 'Status', 'Created'])
        for p in Product.objects.all().order_by('-created_at'):
            profile = getattr(p.vendor, 'vendor_profile', None)
            writer.writerow([
                p.id, p.name,
                profile.brand_name if profile else p.vendor.username,
                p.category.name if p.category else '',
                p.original_price, p.price, p.discount,
                'Active' if p.is_active else 'Hidden',
                p.created_at.strftime('%Y-%m-%d'),
            ])

    elif report_type == 'customers':
        writer.writerow(['ID', 'Username', 'Email', 'Signup Date', 'Favorites', 'Status'])
        for u in User.objects.filter(role=User.CUSTOMER):
            writer.writerow([
                u.id, u.username, u.email,
                u.date_joined.strftime('%Y-%m-%d'),
                Favorite.objects.filter(user=u).count(),
                'Active' if u.is_active else 'Blocked',
            ])

    elif report_type == 'guests':
        writer.writerow(['ID', 'Device ID', 'First Visit', 'Favorites', 'Converted'])
        for u in User.objects.filter(role=User.ANONYMOUS):
            writer.writerow([
                u.id, u.device_id or '',
                u.date_joined.strftime('%Y-%m-%d'),
                Favorite.objects.filter(device_id=u.device_id).count(),
                'Yes' if u.role == User.CUSTOMER else 'No',
            ])

    elif report_type == 'favorites':
        writer.writerow(['Product', 'Vendor', 'Favorites Count'])
        for p in Product.objects.annotate(fav_count=Count('favorited_by')).filter(fav_count__gt=0).order_by('-fav_count'):
            profile = getattr(p.vendor, 'vendor_profile', None)
            writer.writerow([p.name, profile.brand_name if profile else p.vendor.username, p.fav_count])

    return response


# ─── Public vendor profile ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def vendor_public_profile(request, vendor_id):
    vendor = User.objects.filter(id=vendor_id, role=User.VENDOR).first()
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=404)
    profile = getattr(vendor, 'vendor_profile', None)
    if not profile or not profile.is_approved:
        return Response({'error': 'Vendor profile not available'}, status=404)
    logo_url = None
    if profile.logo:
        try:
            logo_url = request.build_absolute_uri(profile.logo.url)
        except Exception:
            logo_url = None
    products = Product.objects.filter(vendor=vendor, is_active=True).order_by('-created_at')
    return Response({
        'id': vendor.id,
        'brand_name': profile.brand_name,
        'logo': logo_url,
        'products': ProductSerializer(products, many=True, context={'request': request}).data
    })
