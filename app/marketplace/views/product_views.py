from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from app.auth.permissions.auth_token import BearerTokenAuthentication
from app.marketplace.models.product import Product, Favorite
from app.marketplace.serializers.product_serializer import ProductSerializer, FavoriteSerializer
from app.auth.models.user import User

@api_view(['GET'])
@permission_classes([AllowAny])
def product_feed(request):
    """Discovery page: all discounted products from all vendors"""
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    
    # Filter by category or brand if provided
    category_id = request.query_params.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
        
    brand_id = request.query_params.get('vendor')
    if brand_id:
        products = products.filter(vendor_id=brand_id)
        
    p_type = request.query_params.get('type')
    if p_type:
        products = products.filter(product_type__icontains=p_type)

    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def upload_product(request):
    """Vendors upload discounted products"""
    if request.user.role != User.VENDOR:
        return Response({'error': 'Only vendors can upload products'}, status=status.HTTP_403_FORBIDDEN)
    
    # Check KYC approval
    if not hasattr(request.user, 'vendor_profile') or not request.user.vendor_profile.is_approved:
        return Response({'error': 'Vendor account is not approved yet'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ProductSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(vendor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def toggle_favorite(request):
    """Save products to favorites (works for guest and registered users)"""
    product_id = request.data.get('product_id')
    device_id = request.data.get('device_id')
    
    if not product_id:
        return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    user = request.user if request.user.is_authenticated else None
    
    if not user and not device_id:
        return Response({'error': 'Authentication or Device ID required'}, status=status.HTTP_401_UNAUTHORIZED)
        
    if user:
        favorite, created = Favorite.objects.get_or_create(user=user, product_id=product_id)
    else:
        favorite, created = Favorite.objects.get_or_create(device_id=device_id, product_id=product_id)
        
    if not created:
        favorite.delete()
        return Response({'message': 'Removed from favorites'})
        
    return Response({'message': 'Added to favorites'})
