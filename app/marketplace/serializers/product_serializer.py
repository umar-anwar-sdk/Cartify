from rest_framework import serializers
from app.marketplace.models.product import Product, Favorite, SubCategory
from app.auth.models.vendor import VendorProfile
from app.scrape.models.scrapeModel import Categories

class ProductSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.vendor_profile.brand_name')
    categories = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'vendor', 'vendor_name', 'categories',
            'name', 'price', 'discount', 'original_price', 'product_type',
            'description', 'image', 'created_at', 'is_active',
            'category', 'subcategory'  # For input
        ]
        read_only_fields = ['vendor', 'created_at']
        extra_kwargs = {
            'name': {'required': True},
            'price': {'required': True},
            'product_type': {'required': True},
            'description': {'required': True},
            'category': {'write_only': True},
            'subcategory': {'write_only': True},
        }

    def get_categories(self, obj):
        category = obj.category
        subcategories = []
        if obj.subcategory:
            subcategories.append({
                'id': obj.subcategory.id,
                'name': obj.subcategory.name
            })
        return [{
            'id': category.id,
            'name': category.name,
            'subcategories': subcategories
        }]

    def validate(self, data):
        # Allow the instance values to be used during partial updates.
        category = data.get('category', getattr(self.instance, 'category', None))
        subcategory = data.get('subcategory', getattr(self.instance, 'subcategory', None))
        price = data.get('price', getattr(self.instance, 'price', None))
        original_price = data.get('original_price', getattr(self.instance, 'original_price', None))

        if original_price and price is not None and price >= original_price:
            raise serializers.ValidationError("Price must be lower than original price for a discounted product.")

        if not category and not subcategory:
            raise serializers.ValidationError({
                'category': 'Category or subcategory is required',
                'subcategory': 'Category or subcategory is required'
            })

        if subcategory:
            if category and subcategory.category_id != category.id:
                raise serializers.ValidationError({'subcategory': 'Subcategory must belong to the chosen category.'})
            category = subcategory.category

        if category and category.subcategories.exists() and not subcategory:
            raise serializers.ValidationError("Please select a subcategory for this category.")

        data['category'] = category
        return data

    def create(self, validated_data):
        if 'subcategory' in validated_data and validated_data.get('subcategory'):
            validated_data['category'] = validated_data['subcategory'].category
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'subcategory' in validated_data and validated_data.get('subcategory'):
            validated_data['category'] = validated_data['subcategory'].category
        return super().update(instance, validated_data)

class FavoriteSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'device_id', 'product', 'product_details', 'created_at']
        read_only_fields = ['user', 'created_at']

class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'name']

class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Categories
        fields = ['id', 'name', 'subcategories']
