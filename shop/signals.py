import os
import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Product, Order
from clinic.models import Customer

@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Notify customer when order status changes"""
    if not created and hasattr(instance, '_old_status') and instance._old_status != instance.status:
        if instance.customer and instance.customer.telegram_id:
            notify_status_update(instance)

@receiver(post_save, sender=Order)
def handle_order_bonus(sender, instance, **kwargs):
    """Add 5% bonus to customer balance when order is delivered"""
    if instance.status == 'DELIVERED' and instance.customer and not instance.bonus_credited:
        bonus_amount = instance.total_price * 0.05
        if bonus_amount > 0:
            with transaction.atomic():
                customer = Customer.objects.select_for_update().get(id=instance.customer.id)
                customer.bonus_balance += bonus_amount
                customer.save()
                
                # Update without triggering signal again
                Order.objects.filter(id=instance.id).update(bonus_credited=True)
                
                # Notify about bonus
                send_telegram_msg(
                    instance.customer.telegram_id,
                    f"🎁 <b>Sizga bonus qo'shildi!</b>\n\n"
                    f"Buyurtmangiz #{instance.id} yakunlanganligi munosabati bilan "
                    f"hisobingizga <b>{bonus_amount:,} so'm</b> bonus qo'shildi. ✨"
                )

def notify_status_update(order):
    """Send status update notification"""
    status_map = {
        'PREPARING': '👨‍🍳 Buyurtmangiz tayyorlanmoqda.',
        'ON_WAY': '🚚 Buyurtmangiz kurerga topshirildi va yo\'lda!',
        'DELIVERED': '✅ Buyurtmangiz muvaffaqiyatli yetkazildi! Rahmat.',
        'CANCELLED': '❌ Buyurtmangiz bekor qilindi.'
    }
    
    msg = status_map.get(order.status)
    if msg:
        full_msg = f"🆔 <b>Order #{order.id} holati yangilandi!</b>\n\n{msg}"
        send_telegram_msg(order.customer.telegram_id, full_msg)

def send_telegram_msg(chat_id, text):
    """Helper for simple notifications"""
    TOKEN = os.getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
         requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Error sending msg: {e}")

@receiver(post_save, sender=Product)
def check_product_stock(sender, instance, **kwargs):
    """Check stock level and send Telegram alert if low"""
    if instance.stock <= instance.min_stock and not instance.notified_low_stock:
        send_low_stock_alert(instance)
        # Update without triggering the signal again
        Product.objects.filter(id=instance.id).update(notified_low_stock=True)
    
    elif instance.stock > instance.min_stock and instance.notified_low_stock:
        # Reset notification flag if stock is replenished
        Product.objects.filter(id=instance.id).update(notified_low_stock=False)

def send_low_stock_alert(product):
    """Send alert via Telegram API"""
    TOKEN = os.getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0")
    # Using a placeholder for admin chat ID if not in env. 
    # In a real scenario, this would be a specific group or admin ID.
    # For now, we'll try to find an admin or use a broadcast if possible, 
    # but Telegram requires a specific chat_id. Let's use the bot owner's placeholder or log it.
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "562723145") # Replacement placeholder
    
    msg = (
        f"🚨 <b>SKLAD OGOHLANTIRISHI</b> 🚨\n\n"
        f"📦 <b>Mahsulot:</b> {product.name}\n"
        f"📉 <b>Qoldiq:</b> {product.stock}\n"
        f"⚠️ <b>Minimal chegara:</b> {product.min_stock}\n\n"
        f"Iltimos, zahirani to'ldiring!"
    )
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": ADMIN_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Error sending low stock alert: {e}")
