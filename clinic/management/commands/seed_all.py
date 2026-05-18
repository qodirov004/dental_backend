import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from clinic.models import Customer, Pet, MedicalRecord, Visit, VaccineSchedule, FollowUp
from shop.models import Product, Order, OrderItem, Category
from billing.models import Invoice, Payment
from users.models import SystemSettings

User = get_user_model()

class Command(BaseCommand):
    help = 'Wipe database and seed with production-ready demo data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting unified seeding process...')
        
        with transaction.atomic():
            # 1. Cleanup
            self.stdout.write('Cleaning up old data...')
            Order.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Visit.objects.all().delete()
            MedicalRecord.objects.all().delete()
            Pet.objects.all().delete()
            Customer.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            
            # 2. Setup Users
            self.stdout.write('Setting up users...')
            # Admin
            admin, _ = User.objects.get_or_create(
                username='admin', 
                defaults={
                    'email': 'admin@vettakhirov.com', 
                    'role': 'ADMIN', 
                    'is_staff': True, 
                    'is_superuser': True
                }
            )
            admin.set_password('admin123')
            admin.save()
            
            # Shop Manager
            shop_manager, _ = User.objects.get_or_create(
                username='shop_manager', 
                defaults={
                    'email': 'shop@vettakhirov.com', 
                    'role': 'SHOP_MANAGER'
                }
            )
            shop_manager.set_password('shop123')
            shop_manager.save()

            # 3. Seed Settings
            SystemSettings.objects.get_or_create(key='admin_telegram_id', defaults={'value': '7102675435', 'description': 'Admin Telegram ID for notifications'})

            # 4. Seed Clinic Data
            self.stdout.write('Seeding clinic data...')
            customers_data = [
                {'name': 'Aliyev Behruz', 'phone': '+998901234567', 'address': 'Tashkent, Chilonzor', 'pets': [
                    {'name': 'Laki', 'species': 'it', 'breed': 'Golden Retriever', 'gender': 'MALE'},
                    {'name': 'Mimi', 'species': 'mushuk', 'breed': 'Siam', 'gender': 'FEMALE'}
                ]},
                {'name': 'Karimova Malika', 'phone': '+998912345678', 'address': 'Tashkent, Shayxontohur', 'pets': [
                    {'name': 'Baron', 'species': 'it', 'breed': 'Nemis ovcharkasi', 'gender': 'MALE'}
                ]},
                {'name': 'Sobirov Jalol', 'phone': '+998934567890', 'address': 'Samarkand, Registon', 'pets': [
                    {'name': 'Qoplon', 'species': 'it', 'breed': 'Alabay', 'gender': 'MALE'}
                ]},
            ]

            all_pets = []
            for c_data in customers_data:
                customer = Customer.objects.create(name=c_data['name'], phone=c_data['phone'], address=c_data['address'])
                for p_data in c_data['pets']:
                    pet = Pet.objects.create(
                        customer=customer,
                        name=p_data['name'],
                        species=p_data['species'],
                        breed=p_data['breed'],
                        gender=p_data['gender'],
                        birth_date=timezone.now().date() - timedelta(days=random.randint(365, 365*3))
                    )
                    all_pets.append(pet)

            # Seed Visits and Medical Records
            for pet in all_pets:
                # History visit
                visit = Visit.objects.create(
                    pet=pet,
                    veterinarian=admin,
                    purpose='Ko\'rik',
                    status='COMPLETED',
                    arrived_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                    total_amount=50000
                )
                MedicalRecord.objects.create(
                    pet=pet,
                    veterinarian=admin,
                    record_type='TREATMENT',
                    diagnosis='Sog\'lom',
                    treatment='Profilaktika',
                    date=visit.arrived_at
                )
                # Invoice for the visit
                Invoice.objects.create(
                    customer=pet.customer,
                    total_amount=50000,
                    status='PAID',
                    created_at=visit.arrived_at
                )

            # 5. Seed Shop Data
            self.stdout.write('Seeding shop data...')
            cats = {
                'FOOD': Category.objects.create(name='Ozuqalar'),
                'MED': Category.objects.create(name='Dorilar'),
                'ACC': Category.objects.create(name='Aksessuarlar')
            }

            products = [
                {'name': 'Royal Canin Adult', 'price': 150000, 'stock': 25, 'cat': 'FOOD'},
                {'name': 'Whiskas Meat', 'price': 55000, 'stock': 40, 'cat': 'FOOD'},
                {'name': 'Antiseptic Spray', 'price': 35000, 'stock': 15, 'cat': 'MED'},
                {'name': 'Smart Collar', 'price': 120000, 'stock': 10, 'cat': 'ACC'},
            ]

            for p_info in products:
                Product.objects.create(
                    name=p_info['name'],
                    price=p_info['price'],
                    stock=p_info['stock'],
                    category=cats[p_info['cat']],
                    description=f"{p_info['name']} haqida ma'lumot"
                )

        self.stdout.write(self.style.SUCCESS('Database wiped and re-seeded successfully!'))
        self.stdout.write(self.style.WARNING('CREDENTIALS:'))
        self.stdout.write(f'  - ADMIN: admin / admin123')
        self.stdout.write(f'  - SHOP:  shop_manager / shop123')
