import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

print("="*60)
print(f"{'Username':<15} | {'Role':<12} | {'Is Active':<10} | {'Is Staff':<10} | {'Has Usable Password':<20}")
print("-"*60)
for u in User.objects.all():
    print(f"{u.username:<15} | {u.role:<12} | {str(u.is_active):<10} | {str(u.is_staff):<10} | {str(u.has_usable_password()):<20}")
print("="*60)
