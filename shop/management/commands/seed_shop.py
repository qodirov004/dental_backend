from django.core.management.base import BaseCommand
from shop.models import Category, Product
from django.core.files import File
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Seeds the database with initial shop products and categories'

    def handle(self, *args, **options):
        self.stdout.write('Seeding shop data...')

        # Categories
        categories = [
            'Oziq-ovqat',
            'O\'yinchoqlar',
            'Gigiena',
            'Dori-darmon',
            'Aksessuarlar'
        ]

        cat_objs = {}
        for cat_name in categories:
            cat, created = Category.objects.get_or_create(name=cat_name)
            cat_objs[cat_name] = cat
            if created:
                self.stdout.write(f'Created category: {cat_name}')

        # Products
        # We will cycle through our 3 placeholder images
        products_data = [
            {
                'name': 'Royal Canin Mushuk Ovqati (2kg)',
                'price': 150000,
                'stock': 50,
                'description': 'Premium sifatli quruq mushuk ovqati. Barcha zotlar uchun mos.',
                'category': 'Oziq-ovqat',
                'image': 'cat_food.png'
            },
            {
                'name': 'Whiskas Tovuqli (400g)',
                'price': 35000,
                'stock': 100,
                'description': 'Tovuq ta\'mli mazali ovqat.',
                'category': 'Oziq-ovqat',
                'image': 'cat_food.png'
            },
            {
                'name': 'Pedigree Kuchuk Ovqati (10kg)',
                'price': 450000,
                'stock': 20,
                'description': 'Katta kuchuklar uchun maxsus ozuqa.',
                'category': 'Oziq-ovqat',
                'image': 'cat_food.png'
            },
            {
                'name': 'Kauchuk Suyak O\'yinchoq',
                'price': 45000,
                'stock': 30,
                'description': 'Chidamli kauchukdan tayyorlangan o\'yinchoq.',
                'category': 'O\'yinchoqlar',
                'image': 'dog_toy.png'
            },
            {
                'name': 'Yumshoq Koptok',
                'price': 25000,
                'stock': 50,
                'description': 'Mushuklar va kuchuklar uchun rangli koptok.',
                'category': 'O\'yinchoqlar',
                'image': 'dog_toy.png'
            },
            {
                'name': 'Tish Tozolovchi Arqon',
                'price': 30000,
                'stock': 40,
                'description': 'Tishlarni tozalashga yordam beruvchi o\'yinchoq.',
                'category': 'O\'yinchoqlar',
                'image': 'dog_toy.png'
            },
            {
                'name': 'Professional Shampun (500ml)',
                'price': 85000,
                'stock': 25,
                'description': 'Moychechak ekstraktli yumshatuvchi shampun.',
                'category': 'Gigiena',
                'image': 'shampoo.png'
            },
            {
                'name': 'Burgaga Qarshi Sprey',
                'price': 60000,
                'stock': 45,
                'description': 'Samarali parazitlarga qarshi vosita.',
                'category': 'Gigiena',
                'image': 'shampoo.png' # Reusing shampoo image as generic hygiene bottle
            },
            {
                'name': 'Tirnoq Olgich',
                'price': 40000,
                'stock': 30,
                'description': 'Xavfsiz tirnoq olish uchun maxsus qaychi.',
                'category': 'Gigiena',
                'image': 'shampoo.png' # Placeholder
            },
            {
                'name': 'Vitamin Kompleks',
                'price': 90000,
                'stock': 60,
                'description': 'Immunitetni mustahkamlash uchun vitaminlar.',
                'category': 'Dori-darmon',
                'image': 'cat_food.png' # Placeholder
            },
            {
                'name': 'Charm Bo\'yinbog\'',
                'price': 55000,
                'stock': 20,
                'description': 'Haqiqiy charmdan tayyorlangan mustahkam bo\'yinbog\'.',
                'category': 'Aksessuarlar',
                'image': 'dog_toy.png' # Placeholder
            }
        ]

        media_root = settings.MEDIA_ROOT
        products_dir = os.path.join(media_root, 'products')

        for p_data in products_data:
            # Check if exists
            if Product.objects.filter(name=p_data['name']).exists():
                self.stdout.write(f"Product {p_data['name']} already exists. Skipping.")
                continue

            category = cat_objs.get(p_data['category'])
            
            product = Product(
                name=p_data['name'],
                price=p_data['price'],
                stock=p_data['stock'],
                description=p_data['description'],
                category=category,
                discount_percent=0
            )

            # Handle Image
            image_path = os.path.join(products_dir, p_data['image'])
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    # We copy it to a new file in fields to avoid moving the source?
                    # Django ImageField save method will handle duplications if names conflict, usually.
                    # But simpler to just reference if we can? 
                    # No, better to verify we can construct proper ImageField.
                    # We will simply save it into the field.
                    product.image.save(p_data['image'], File(f), save=False)
            
            product.save()
            self.stdout.write(f"Created product: {p_data['name']}")

        self.stdout.write(self.style.SUCCESS('Shop seeded successfully!'))
