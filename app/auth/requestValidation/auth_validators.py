from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re

User = get_user_model()

class RegisterValidator:
    def __init__(self, data, files=None):
        self.data = data
        self.files = files or {}
        self.errors = {}
        self.role = self.data.get('role', User.CUSTOMER).upper()
    
    def validate(self):
        self._validate_role()
        self._validate_required_fields()
        self._validate_vendor_fields()
        self._validate_email()
        self._validate_username()
        self._validate_password()
        self._validate_location()
        return len(self.errors) == 0
    
    def _validate_location(self):
        # Location fields are now mandatory
        location_fields = ['country', 'state', 'city', 'latitude', 'longitude']
        for field in location_fields:
            if not self.data.get(field):
                self.errors[field] = f"{field.replace('_', ' ').capitalize()} is required"
        
        lat = self.data.get('latitude')
        lng = self.data.get('longitude')
        if lat:
            try:
                f_lat = float(lat)
                if f_lat < -90 or f_lat > 90:
                    self.errors['latitude'] = "Latitude must be between -90 and 90"
            except (ValueError, TypeError):
                self.errors['latitude'] = "Latitude must be a number"
        if lng:
            try:
                f_lng = float(lng)
                if f_lng < -180 or f_lng > 180:
                    self.errors['longitude'] = "Longitude must be between -180 and 180"
            except (ValueError, TypeError):
                self.errors['longitude'] = "Longitude must be a number"
    
    def _validate_role(self):
        if self.role not in [User.CUSTOMER, User.VENDOR]:
            self.errors['role'] = 'Invalid role'
    
    def _validate_required_fields(self):
        required = ['first_name', 'last_name', 'username', 'email', 'password']
        customer_errors = {}
        for field in required:
            if not self.data.get(field):
                customer_errors[field] = f"{field} is required"
        if customer_errors:
            self.errors['customer_fields'] = customer_errors
    
    def _validate_vendor_fields(self):
        if self.role == User.VENDOR:
            required = ['brand_name', 'phone_number', 'address']
            vendor_errors = {}
            for field in required:
                if not self.data.get(field):
                    vendor_errors[field] = f"{field} is required for vendor registration"
            if not self.files.get('logo'):
                vendor_errors['logo'] = "Brand logo is required for vendor registration"
                
            if vendor_errors:
                self.errors['vendor_fields'] = vendor_errors
    
    def _validate_email(self):
        email = self.data.get('email')
        if email:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                self.errors['email'] = "Invalid email format"
            elif User.objects.filter(email=email).exists():
                self.errors['email'] = "Email already exists"
    
    def _validate_username(self):
        username = self.data.get('username')
        if username:
            if User.objects.filter(username=username).exists():
                self.errors['username'] = "Username already exists"
    
    def _validate_password(self):
        password = self.data.get('password')
        if password and len(password) < 8:
            self.errors['password'] = "Password must be at least 8 characters"

class LoginValidator:
    def __init__(self, data):
        self.data = data
        self.errors = {}
    
    def validate(self):
        if not self.data.get('username_or_email'):
            self.errors['username_or_email'] = "Username or email is required"
        if not self.data.get('password'):
            self.errors['password'] = "Password is required"
        return len(self.errors) == 0

class ResetPasswordValidator:
    def __init__(self, data):
        self.data = data
        self.errors = {}
    
    def validate(self):
        if not self.data.get('email'):
            self.errors['email'] = "Email is required"
        elif not User.objects.filter(email=self.data.get('email')).exists():
            self.errors['email'] = "Email not found"
        return len(self.errors) == 0

class ConfirmResetValidator:
    def __init__(self, data):
        self.data = data
        self.errors = {}
    
    def validate(self):
        if not self.data.get('email'):
            self.errors['email'] = "Email is required"
        if not self.data.get('otp'):
            self.errors['otp'] = "OTP is required"
        if not self.data.get('new_password'):
            self.errors['new_password'] = "New password is required"
        elif len(self.data.get('new_password', '')) < 8:
            self.errors['new_password'] = "Password must be at least 8 characters"
        return len(self.errors) == 0