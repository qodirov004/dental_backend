import os
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from clinic.models import VaccineSchedule

class Command(BaseCommand):
    help = 'Send Telegram reminders for upcoming vaccines'

    def handle(self, *args, **options):
        # Look for vaccines in the next 7 days
        reminder_window = timezone.now().date() + timedelta(days=7)
        upcoming_vaccines = VaccineSchedule.objects.filter(
            next_date__lte=reminder_window,
            next_date__gte=timezone.now().date(),
            notified=False,
            pet__customer__telegram_id__isnull=False
        )

        self.stdout.write(f"Found {upcoming_vaccines.count()} upcoming vaccines to notify.")

        TOKEN = os.getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0")
        
        for schedule in upcoming_vaccines:
            customer = schedule.pet.customer
            pet = schedule.pet
            
            msg = (
                f"💉 <b>Vaksina eslatmasi!</b> 🐾\n\n"
                f"Hurmatli {customer.name},\n"
                f"Sizning <b>{pet.name}</b> ismli hayvoningiz uchun <b>{schedule.vaccine_name}</b> vaksinasini olish vaqti yaqinlashmoqda.\n\n"
                f"📅 <b>Sana:</b> {schedule.next_date.strftime('%d.%m.%Y')}\n\n"
                f"Iltimos, qabulga yozilishni unutmang! 😊"
            )
            
            import json
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            
            kb = {
                "inline_keyboard": [
                    [{"text": "🏥 Qabulga yozilish", "url": f"https://t.me/{(TOKEN.split(':')[0])}?start=appointment"}]
                ]
            }

            try:
                res = requests.post(url, json={
                    "chat_id": customer.telegram_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "reply_markup": kb
                })
                if res.status_code == 200:
                    schedule.notified = True
                    schedule.save()
                    self.stdout.write(self.style.SUCCESS(f"Successfully notified {customer.name} about {pet.name}'s vaccine."))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to send message to {customer.name}: {res.text}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error sending message to {customer.name}: {str(e)}"))
