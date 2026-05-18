import random
from django.core.management.base import BaseCommand
from shop.models import Order, OrderItem, Product
from clinic.models import Customer
from users.models import SystemSettings
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seed database with demo Bot Orders and Settings'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding Bot Orders...')
        
        # 1. Set Admin ID
        SystemSettings.objects.update_or_create(
            key='admin_telegram_id',
            defaults={'value': '99890123', 'description': 'Demo Admin ID'}
        )
        
        # 2. Get prerequisites
        products = list(Product.objects.all())
        if not products:
            self.stdout.write(self.style.ERROR('No products found. Run seed_demo first.'))
            return

        # 3. Create Orders
        center_lat = 41.2995
        center_lon = 69.2401
        
        for i in range(5):
            # Random offset for location (approx 1-5km)
            lat = center_lat + random.uniform(-0.03, 0.03)
            lon = center_lon + random.uniform(-0.03, 0.03)
            
            customer_name = random.choice(["Botir", "Sardor", "Malika", "Aziza", "Jasur"])
            
            order = Order.objects.create(
                customer_name=f"{customer_name} (Telegram)",
                status='NEW',
                source='TELEGRAM_BOT',
                latitude=lat,
                longitude=lon,
                created_at=timezone.now()
            )
            
            # Add items
            total = 0
            for _ in range(random.randint(1, 4)):
                prod = random.choice(products)
                qty = random.randint(1, 3)
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    price=prod.price
                )
                total += (prod.price * qty)
            
            order.total_price = total
            order.save()
            
            self.stdout.write(f"Created Bot Order #{order.id} at {lat}, {lon}")

        self.stdout.write(self.style.SUCCESS('Bot Orders seeded successfully!'))
