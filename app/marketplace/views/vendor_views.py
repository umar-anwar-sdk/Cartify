from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from app.auth.permissions.auth_token import BearerTokenAuthentication
from app.auth.models.user import User
from app.auth.models.vendor import VendorProfile
from django.core.exceptions import ValidationError
from django.db import transaction

@api_view(['PATCH'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_vendor_profile(request):
    """Vendor updates their own brand profile, including logo"""
    if request.user.role != User.VENDOR:
        return Response({'error': 'Only vendors can update their profile'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        profile = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    
    # Fields allowed to be updated by vendor
    allowed_fields = ['brand_name', 'phone_number', 'email', 'address']
    
    with transaction.atomic():
        for field in allowed_fields:
            if field in data:
                setattr(profile, field, data[field])
        
        # Handle logo upload (ImageField)
        if 'logo' in request.FILES:
            profile.logo = request.FILES['logo']
            
        profile.save()

    return Response({
        'message': 'Profile updated successfully',
        'brand_name': profile.brand_name,
        'logo': profile.logo.url if profile.logo else None
    })

@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def vendor_products(request):
    """Vendor gets all of their own products"""
    if request.user.role != User.VENDOR:
        return Response({'error': 'Only vendors can view their products'}, status=status.HTTP_403_FORBIDDEN)
    
    from app.marketplace.models.product import Product
    from app.marketplace.serializers.product_serializer import ProductSerializer
    
    products = Product.objects.filter(vendor=request.user).order_by('-created_at')
    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['PATCH'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def edit_vendor_product(request, product_id):
    """Vendor edits their own product"""
    if request.user.role != User.VENDOR:
        return Response({'error': 'Only vendors can edit products'}, status=status.HTTP_403_FORBIDDEN)
    
    from app.marketplace.models.product import Product
    from app.marketplace.serializers.product_serializer import ProductSerializer
    
    product = Product.objects.filter(id=product_id, vendor=request.user).first()
    if not product:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
    data = request.data
    for field in ['name', 'description', 'price', 'original_price', 'discount', 'is_active', 'category', 'subcategory']:
        if field in data:
            setattr(product, field, data[field])
            
    # Handle image update if necessary
    if 'image' in request.FILES:
        product.image = request.FILES['image']
    try:
        product.full_clean()
    except ValidationError as e:
        return Response({'error': e.message_dict if hasattr(e, 'message_dict') else e.messages}, status=400)
    product.save()
    return Response(ProductSerializer(product, context={'request': request}).data)


@api_view(['DELETE'])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_vendor_product(request, product_id):
    """Vendor deletes their own product"""
    if request.user.role != User.VENDOR:
        return Response({'error': 'Only vendors can delete products'}, status=status.HTTP_403_FORBIDDEN)
    
    from app.marketplace.models.product import Product
    
    product = Product.objects.filter(id=product_id, vendor=request.user).first()
    if not product:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
    product.delete()
    return Response({'message': 'Product deleted successfully'})
