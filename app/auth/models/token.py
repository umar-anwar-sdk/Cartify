# import secrets
# from django.db import models
# from django.contrib.auth import get_user_model

# User = get_user_model()

# class Token(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
#     key = models.CharField(max_length=40, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     def save(self, *args, **kwargs):
#         if not self.key:
#             self.key = self.generate_key()
#         return super().save(*args, **kwargs)
    
#     def generate_key(self):
#         return secrets.token_hex(20)
    
#     def __str__(self):
#         return self.key
import secrets
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Token(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
	key = models.CharField(max_length=40, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.key:
			self.key = self.generate_key()
		return super().save(*args, **kwargs)

	def generate_key(self):
		return secrets.token_hex(20)

	def __str__(self):
		return self.key