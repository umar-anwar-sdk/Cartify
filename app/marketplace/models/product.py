from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from app.scrape.models.scrapeModel import Categories

class SubCategory(models.Model):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class Product(models.Model):
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_products')

    category = models.ForeignKey(Categories, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    product_type = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    image = models.ImageField(upload_to='product_images/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        # CASE 1: Subcategory selected
        if self.subcategory:
            if self.subcategory.category != self.category:
                raise ValidationError("Subcategory must belong to selected category")

        # CASE 2: No subcategory
        else:
            if self.category.subcategories.exists():
                raise ValidationError(
                    "This category has subcategories. You must select a subcategory."
                )

    def save(self, *args, **kwargs):
        self.clean()  # enforce validation on save
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='favorites')
    device_id = models.CharField(max_length=255, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product') # One favorite per product for registered users
        # For anonymous, we rely on device_id in logic
