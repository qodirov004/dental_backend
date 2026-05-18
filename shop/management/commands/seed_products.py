from django.core.management.base import BaseCommand
from shop.models import Product

class Command(BaseCommand):
    help = 'Seeds products with rich demo data'

    def handle(self, *args, **kwargs):
        products = [
            # Food
            {
                "name": "Royal Canin Mini Adult",
                "price": 180000,
                "description": "Kichik zotli itlar uchun maxsus ozuqa. 2kg.",
                "stock": 50,
                "category": "Oziq-ovqat",
                "image": "https://placehold.co/400x400/png?text=Royal+Canin"
            },
            {
                "name": "Whiskas Tovuqli Rag",
                "price": 6000,
                "description": "Mushuklar uchun nam ozuqa (jele). 85g.",
                "stock": 200,
                "category": "Oziq-ovqat",
                "image": "https://placehold.co/400x400/png?text=Whiskas"
            },
            {
                "name": "Pedigree DentaStix",
                "price": 25000,
                "description": "Itlar tishlarini tozalash uchun chaynash tayoqchalari.",
                "stock": 100,
                "category": "Oziq-ovqat",
                "image": "https://placehold.co/400x400/png?text=Pedigree"
            },
            {
                "name": "ProPlan Sterilised",
                "price": 210000,
                "description": "Sterilizatsiya qilingan mushuklar uchun quruq ozuqa. 1.5kg.",
                "stock": 30,
                "category": "Oziq-ovqat",
                "image": "https://placehold.co/400x400/png?text=ProPlan"
            },
            
            # Toys
            {
                "name": "Rezina Koptok",
                "price": 15000,
                "description": "Chidamli rezina koptok, itlar uchun.",
                "stock": 50,
                "category": "O'yinchoqlar",
                "image": "https://placehold.co/400x400/png?text=Koptok"
            },
             {
                "name": "Sichqoncha (mexanik)",
                "price": 20000,
                "description": "Burama mexanizmli o'yinchoq sichqon.",
                "stock": 40,
                "category": "O'yinchoqlar",
                "image": "https://placehold.co/400x400/png?text=Sichqoncha"
            },
            {
                "name": "Arqonli Suyak",
                "price": 35000,
                "description": "Itlar tishlashini yaxshilash uchun arqonli o'yinchoq.",
                "stock": 25,
                "category": "O'yinchoqlar",
                "image": "https://placehold.co/400x400/png?text=Arqon"
            },

            # Medicine
            {
                "name": "Bravecto (4.5-10kg)",
                "price": 350000,
                "description": "Burgalar va kanalarga qarshi tabletka. 1 dona.",
                "stock": 10,
                "category": "Dori-darmon",
                "image": "https://placehold.co/400x400/png?text=Bravecto"
            },
            {
                "name": "Gelmintal sirop",
                "price": 45000,
                "description": "Gijjalarga qarshi suspenziya. 10ml.",
                "stock": 60,
                "category": "Dori-darmon",
                "image": "https://placehold.co/400x400/png?text=Gelmintal"
            },
            {
                "name": "Advocate tomchilari",
                "price": 120000,
                "description": "Yag'irga qarshi tomchilar (Spot-on).",
                "stock": 15,
                "category": "Dori-darmon",
                "image": "https://placehold.co/400x400/png?text=Advocate"
            },

            # Accessories
            {
                "name": "Charm Bo'yinbog' (L)",
                "price": 85000,
                "description": "Katta itlar uchun haqiqiy charm bo'yinbog'.",
                "stock": 20,
                "category": "Aksessuarlar",
                "image": "https://placehold.co/400x400/png?text=Boyinbog"
            },
             {
                "name": "Taroq (Pnx)",
                "price": 30000,
                "description": "Uy hayvonlari junini tarash uchun.",
                "stock": 45,
                "category": "Aksessuarlar",
                "image": "https://placehold.co/400x400/png?text=Taroq"
            },
             {
                "name": "Mushuklar uyi",
                "price": 450000,
                "description": "Yumshoq yostiqli qulay uy.",
                "stock": 5,
                "category": "Aksessuarlar",
                "image": "https://placehold.co/400x400/png?text=Uy"
            },
        ]

        count = 0
        for p_data in products:
            obj, created = Product.objects.update_or_create(
                name=p_data['name'], 
                defaults=p_data
            )
            if created:
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded/updated products. New items: {count}'))
