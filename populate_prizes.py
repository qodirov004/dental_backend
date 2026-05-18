import os
import django
import random
from io import BytesIO
from django.core.files.base import ContentFile

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from games.models import GamePrize

def generate_placeholder_image(color, text=""):
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (300, 300), color=color)
        # We won't add text to avoid font path issues, color is enough for placeholder
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        return ContentFile(img_io.getvalue())
    except ImportError:
        print("⚠️ Pillow o'rnatilmagan")
        return None

def populate_prizes():
    print("🚀 Yutuqlar yuklanmoqda...")

    prizes = [
        {
            "name": "Omad kelmadi 😢",
            "coeff": 50.0,
            "limit": 1000,
            "desc": "Keyingi safar albatta omad kulib boqadi!",
            "color": "#808080" # Grey
        },
        {
            "name": "5% Chegirma",
            "coeff": 25.0,
            "limit": 100,
            "desc": "Barcha mahsulotlar uchun 5% chegirma kuponi.",
            "color": "#FFD700" # Gold
        },
        {
            "name": "Bepul Yetkazib Berish 🚚",
            "coeff": 15.0,
            "limit": 50,
            "desc": "Toshkent shahri bo'ylab bepul dastavka.",
            "color": "#00CED1" # Turquoise
        },
        {
            "name": "10% Chegirma 🔥",
            "coeff": 8.0,
            "limit": 20,
            "desc": "Katta chegirma!",
            "color": "#FF4500" # OrangeRed
        },
        {
            "name": "Kichik Sovg'a 🎁",
            "coeff": 2.0,
            "limit": 5,
            "desc": "Do'konimizdan maxsus sovg'a.",
            "color": "#9370DB" # MediumPurple
        }
    ]

    for p in prizes:
        if GamePrize.objects.filter(name=p['name']).exists():
            print(f"⚠️ Mavjud: {p['name']}")
            continue
            
        print(f"📥 Yaratilmoqda: {p['name']}...")
        
        prize = GamePrize(
            name=p['name'],
            coefficient=p['coeff'],
            daily_limit=p['limit'],
            description=p['desc'],
            is_active=True
        )
        
        img_file = generate_placeholder_image(p['color'])
        if img_file:
            random_id = random.randint(1000, 9999)
            prize.image.save(f"prize_{random_id}.png", img_file, save=True)
        else:
            prize.save()
            
        print(f"✅ Yaratildi: {p['name']}")

    print("\n🎉 Barchasi yakunlandi!")

if __name__ == "__main__":
    populate_prizes()
