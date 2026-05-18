import os
import django
import random
from io import BytesIO
from django.core.files.base import ContentFile

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from shop.models import Category, Product, Supplier

def generate_placeholder_image(text, color):
    try:
        from PIL import Image, ImageDraw, ImageFont
        # Create a new image with a solid color
        img = Image.new('RGB', (400, 400), color=color)
        d = ImageDraw.Draw(img)
        
        # Add text (optional, basics)
        # We won't load a fancy font to avoid path issues, just drawing simple text or shapes
        # For simplicity in this script, we just return the colored block
        
        # Save to BytesIO
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        return ContentFile(img_io.getvalue())
    except ImportError:
        print("⚠️ Pillow (PIL) o'rnatilmagan, rasm yaratilmadi.")
        return None

def populate():
    print("🚀 Boshlanyapti... (Lokal rasm generatsiya qilinmoqda)")

    # 1. Create Suppliers
    supplier, _ = Supplier.objects.get_or_create(
        name="Best Pet Supplies", 
        contact="+998901234567"
    )

    # 2. Create Categories
    categories = {
        "Itlar uchun ozuqa": "dog-food",
        "Mushuklar uchun ozuqa": "cat-food", 
        "O'yinchoqlar": "toys",
        "Vitaminlar": "vitamins"
    }
    
    cat_objs = {}
    for name, slug in categories.items():
        cat, created = Category.objects.get_or_create(name=name)
        cat_objs[slug] = cat
        print(f"✅ Kategoriya: {name}")

    # 3. Products Data
    products_data = [
        {
            "name": "Royal Canin Mini Adult",
            "cat": "dog-food",
            "price": 450000,
            "desc": "Kichik zotli itlar uchun to'laqonli ozuqa. 10 oylikdan 8 yoshgacha.",
            "color": "#E31B23" # Red
        },
        {
            "name": "Pedigree Dlya Shanks",
            "cat": "dog-food", 
            "price": 32000,
            "desc": "Mol go'shti bilan jele. Barcha zotlar uchun.",
            "color": "#F3BD21" # Yellow
        },
        {
            "name": "Whiskas Tovuq Go'shti",
            "cat": "cat-food",
            "price": 6000,
            "desc": "Mushukchalar uchun jele. 85g.",
            "color": "#532D8E" # Purple
        },
        {
            "name": "Felix Sensations",
            "cat": "cat-food",
            "price": 7500,
            "desc": "Jele ichidagi go'sht bo'laklari.",
            "color": "#009FE3" # Blue
        },
        {
            "name": "Kauchuk Suyak",
            "cat": "toys",
            "price": 45000,
            "desc": "Itlar tishlashini yaxshilash uchun mustahkam o'yinchoq.",
            "color": "#FFC0CB" # Pink
        },
        {
            "name": "Sichqoncha",
            "cat": "toys",
            "price": 15000,
            "desc": "Mushuklar uchun yumshoq o'yinchoq.",
            "color": "#808080" # Grey
        },
        {
            "name": "Multivitamin Complex 8in1",
            "cat": "vitamins",
            "price": 120000,
            "desc": "Barcha turdagi hayvonlar uchun umumiy quvvatlovchi vitaminlar.",
            "color": "#FF8C00" # Orange
        }
    ]

    # 4. Create Products
    for p in products_data:
        if Product.objects.filter(name=p["name"]).exists():
            print(f"⚠️ Mavjud: {p['name']}")
            continue

        print(f"📥 Yaratilmoqda: {p['name']}...")
        
        try:
            img_file = generate_placeholder_image(p['name'], p['color'])
            img_name = f"{p['cat']}_{random.randint(1000,9999)}.png"
            
            product = Product(
                name=p['name'],
                category=cat_objs[p['cat']],
                price=p['price'],
                description=p['desc'],
                supplier=supplier,
                stock=random.randint(10, 100),
                min_stock=5
            )
            if img_file:
                product.image.save(img_name, img_file, save=True)
            else:
                product.save()
                
            print(f"✅ Yaratildi: {p['name']}")

        except Exception as e:
            print(f"❌ Xatolik: {e}")

    print("\n🎉 Barchasi yakunlandi!")

if __name__ == "__main__":
    populate()
