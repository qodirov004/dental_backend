from celery import shared_task
from django.utils import timezone
from .models import VaccineSchedule
from datetime import timedelta
from asgiref.sync import async_to_sync
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from os import getenv

# Load bot token from env or use existing one
TOKEN = getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0") 

@shared_task
def check_vaccinations():
    today = timezone.now().date()
    # Check for vaccines due in 2 days or 1 day
    upcoming_vaccines = VaccineSchedule.objects.filter(
        next_date__in=[today + timedelta(days=1), today + timedelta(days=2)]
    )

    for schedule in upcoming_vaccines:
        pet = schedule.pet
        customer = pet.customer
        if customer.telegram_id:
            message = (
                f"🔔 <b>Eslatma!</b>\n\n"
                f"Hurmatli {customer.name}, sizning {pet.name} nomli hayvoningiz uchun "
                f"<b>{schedule.vaccine_name}</b> vaksinasi muddati yaqinlashmoqda.\n"
                f"Sana: {schedule.next_date}\n\n"
                f"Iltimos, klinikaga tashrif buyuring."
            )
            # Send message via Bot
            # async_to_sync is needed because Celery is sync, aiogram is async
            try:
                async_to_sync(send_telegram_message)(customer.telegram_id, message)
            except Exception as e:
                print(f"Failed to send message to {customer.name}: {e}")

async def send_telegram_message(chat_id, text):
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.send_message(chat_id=chat_id, text=text)
    await bot.session.close()

@shared_task
def check_batch_expiry():
    from shop.models import ProductBatch
    from users.models import SystemSettings
    
    today = timezone.now().date()
    # Alert for items expiring in exactly 30, 7, 3 days
    targets = [30, 7, 3]
    
    for days in targets:
        target_date = today + timedelta(days=days)
        batches = ProductBatch.objects.filter(expiry_date=target_date, quantity__gt=0)
        
        if batches.exists():
            try:
                admin_setting = SystemSettings.objects.get(key='admin_telegram_id')
                admin_id = admin_setting.value
                
                message = f"⚠️ <b>Sklad Ogohlantirish! ({days} kun qoldi)</b>\n\n"
                for batch in batches:
                    message += f"▫️ {batch.product.name} (Batch: {batch.batch_id})\n   Soni: {batch.quantity}, Sana: {batch.expiry_date}\n\n"
                
                async_to_sync(send_telegram_message)(admin_id, message)
            except Exception as e:
                print(f"Error sending batch expiry alert: {e}")

@shared_task
def check_followups():
    from .models import FollowUp
    
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    # 1. Notify for tomorrow (1 day before)
    # Filter where scheduled_date is tomorrow AND notified_1d is False
    # Also ignore if completed
    followups_tomorrow = FollowUp.objects.filter(
        scheduled_date=tomorrow, 
        is_completed=False, 
        notified_1d=False
    )
    
    for fu in followups_tomorrow:
        pet = fu.visit.pet
        customer = pet.customer
        if customer.telegram_id:
            msg = (
                f"🔔 <b>Eslatma (Ertaga)!</b>\n\n"
                f"Hurmatli {customer.name}, {pet.name} uchun ertaga ({fu.scheduled_date}) qayta ko'rik belgilangan.\n"
                f"Iltimos, kechikmasdan kelishingizni so'raymiz."
            )
            try:
                async_to_sync(send_telegram_message)(customer.telegram_id, msg)
                fu.notified_1d = True
                fu.save()
            except Exception:
                pass

    # 2. Notify for TODAY (Morning reminder)
    followups_today = FollowUp.objects.filter(
        scheduled_date=today,
        is_completed=False,
        notified_today=False
    )

    for fu in followups_today:
        pet = fu.visit.pet
        customer = pet.customer
        if customer.telegram_id:
            msg = (
                f"🔔 <b>Bugun Qayta Ko'rik!</b>\n\n"
                f"Hurmatli {customer.name}, bugun {pet.name} bilan klinikaga kelishingizni kutmoqdamiz."
            )
            try:
                async_to_sync(send_telegram_message)(customer.telegram_id, msg)
                fu.notified_today = True
                fu.save()
            except Exception:
                pass
