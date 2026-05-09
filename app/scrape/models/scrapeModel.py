from django.db import models
from django.conf import settings

class ScrapedProduct(models.Model):
    User_name=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    url = models.URLField()
    category=models.ForeignKey('categories', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.TextField(max_length=500, blank=True ,null=True)
    price = models.TextField(max_length=100, blank=True, null=True)
    images = models.JSONField(default=list, blank=True ,null=True)
    description = models.TextField(blank=True, null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scraped_at']
    
        
class Categories(models.Model):
    User_name=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(unique=False ,max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    
class productClick(models.Model):
    User_name=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    product=models.ForeignKey(ScrapedProduct, on_delete=models.CASCADE, null=True, blank=True)
    scrape_click_count=models.IntegerField(null=True, blank=True)
    web_click_count=models.IntegerField(null=True ,blank=True )
    
    def __str__(self):
        return f"{self.product.title} - {self.click_count} - {self.web_click_count} clicks"    