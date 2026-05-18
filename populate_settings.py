import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import SystemSettings

def populate_defaults():
    print("🚀 Sozlamalar tekshirilmoqda...")

    defaults = {
        "bot_token": "SIZNING_BOT_TOKENINGIZ",
        "admin_telegram_id": "SIZNING_ID_RAQAMINGIZ",
        "webapp_url": "https://vetakhirovapp.vercel.app",
        "contact_address": "Toshkent sh., Mirzo Ulug'bek tumani",
        "contact_phone": "+998 90 123 45 67",
        "contact_message": "Biz ijtimoiy tarmoqlarda:\nInstagram: @vettakhirov\nTelegram: @vettakhirov_channel"
    }

    for key, val in defaults.items():
        obj, created = SystemSettings.objects.get_or_create(key=key)
        if created:
            obj.value = val
            obj.description = "Avtomatik yaratilgan sozlama"
            obj.save()
            print(f"✅ Yaratildi: {key}")
        else:
            print(f"ℹ️ Mavjud: {key} (O'zgartirilmadi)")

    print("\n🎉 Barchasi tayyor!")

if __name__ == "__main__":
    populate_defaults()
