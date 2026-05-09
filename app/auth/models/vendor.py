from django.db import models
from django.conf import settings

class VendorProfile(models.Model):
    KYC_PENDING = 'PENDING'
    KYC_APPROVED = 'APPROVED'
    KYC_REJECTED = 'REJECTED'
    
    KYC_STATUS_CHOICES = [
        (KYC_PENDING, 'Pending'),
        (KYC_APPROVED, 'Approved'),
        (KYC_REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_profile')
    brand_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    logo = models.ImageField(upload_to='vendor_logos/', null=True, blank=True)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default=KYC_PENDING)
    rejection_reason = models.TextField(null=True, blank=True)
    is_approved = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.brand_name
