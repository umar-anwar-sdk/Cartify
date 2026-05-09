from django.db import models
from django.conf import settings
from app.scrape.models.scrapeModel import Categories

class VendorCategorySetting(models.Model):
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='category_settings')
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)
    is_disabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ('vendor', 'category')

    def __str__(self):
        status = "Disabled" if self.is_disabled else "Enabled"
        return f"{self.vendor.username} - {self.category.name} ({status})"
