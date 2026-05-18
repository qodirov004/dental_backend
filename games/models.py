from django.db import models
from django.conf import settings
from shop.models import Product
import random
import string


class GameSettings(models.Model):
    daily_referral_limit = models.IntegerField(default=5, help_text="Max referral spins per user per day")
    fraud_threshold_ip = models.IntegerField(default=3, help_text="Max clean registrations from same IP (if tracking IP)")
    
    class Meta:
        verbose_name = "Game Settings"
        verbose_name_plural = "Game Settings"

    def __str__(self):
        return "Global Game Settings"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class GamePrize(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='prizes/')
    coefficient = models.FloatField(help_text="Probability weight (0.1 - 100)")
    daily_limit = models.IntegerField(default=10, help_text="Max wins per day globally")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True, null=True, help_text="What is this prize?")
    instructions = models.TextField(blank=True, null=True, help_text="How to use/claim it?")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (x{self.coefficient})"

class UserWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.IntegerField(default=0, help_text="Virtual currency (Diamonds/Coins)")
    spins = models.IntegerField(default=1, help_text="Available spins")
    total_spins = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.balance} coins"

class GameSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) # Made nullable as bot users might play
    customer = models.ForeignKey('clinic.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    prize = models.ForeignKey(GamePrize, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_win = models.BooleanField(default=False)
    coupon_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.coupon_code:
            self.coupon_code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        # Requirements: 4 chars, unique, mix of letters/numbers.
        chars = string.ascii_uppercase + string.digits
        while True:
            # Generate 4-char code
            code = ''.join(random.choices(chars, k=4))
            
            # Ensure mixture of letters and numbers
            if code.isdigit() or code.isalpha():
                continue 
                
            if not GameSession.objects.filter(coupon_code=code).exists():
                return code

    def __str__(self):
        user_name = self.user.username if self.user else (self.customer.name if self.customer else "Unknown")
        return f"Session {self.id} - {user_name}"
