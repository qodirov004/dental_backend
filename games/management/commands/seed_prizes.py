from django.core.management.base import BaseCommand
from games.models import GamePrize
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Seeds default game prizes with images'

    def handle(self, *args, **kwargs):
        prizes = [
            {
                "name": "5% Skidka", 
                "coefficient": 50, 
                "image": "prizes/prize_5_percent.png",
                "description": "Barcha mahsulotlar uchun 5% chegirma.",
                "instructions": "Ushbu chegirmani faollashtirish uchun buyurtma berish vaqtida 'Mening yutuqlarim' bo'limidan ushbu kuponni tanlang. Chegirma avtomatik ravishda hisoblanadi."
            },
            {
                "name": "10% Skidka", 
                "coefficient": 20, 
                "image": "prizes/prize_10_percent.png",
                "description": "Barcha mahsulotlar uchun 10% super chegirma.",
                "instructions": "Savatchadagi mahsulotlar uchun to'lov qilishdan oldin ushbu yutuqni tanlang. 10% chegirma darhol qo'llaniladi."
            },
            {
                "name": "Bepul Yetkazib Berish", 
                "coefficient": 15, 
                "image": "prizes/prize_free_delivery.png",
                "description": "Buyurtmangizni uyingizgacha bepul yetkazib beramiz.",
                "instructions": "Buyurtmani rasmiylashtirishda yetkazib berish usulini tanlang va ushbu yutuqni qo'llang. Yetkazib berish narxi 0 so'm bo'ladi."
            },
            {
                "name": "Qayta Urinib Koring", 
                "coefficient": 40, 
                "image": "prizes/prize_try_again.png",
                "description": "Afsuski bu safar omadingiz kelmadi.",
                "instructions": "Yana bir bor urinib ko'ring! Keyingi safar albatta yutasiz."
            },
            {
                "name": "Oyinchoq Sovga", 
                "coefficient": 5, 
                "image": "prizes/prize_toy_gift.png",
                "description": "Maxsus yumshoq o'yinchoq sovg'a.",
                "instructions": "Yutuqni olish uchun eng yaqin filialimizga murojaat qiling va yutuq kodini ko'rsating. Yoki navbatdagi buyurtmangizga qo'shib beramiz."
            },
        ]
        
        for data in prizes:
            # We use update_or_create to ensure images are updated if prize exists
            p, created = GamePrize.objects.update_or_create(
                name=data['name'],
                defaults={
                    "coefficient": data['coefficient'],
                    "is_active": True,
                    "image": data['image'],
                    "description": data['description'],
                    "instructions": data['instructions']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created prize: {p.name}"))
            else:
                self.stdout.write(f"Updated prize: {p.name}")
