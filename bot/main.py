import asyncio
import logging
import sys
import os
import django
import re
from os import getenv

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from clinic.models import Customer, Pet, Visit, VaccineSchedule
from games.models import GameSettings
from asgiref.sync import sync_to_async
from django.utils import timezone

# Load from env or use placeholder
TOKEN = getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0") 

# States
class BookingState(StatesGroup):
    selecting_pet = State()
    selecting_purpose = State()

class OrderState(StatesGroup):
    waiting_for_phone = State()
    confirm_existing_phone = State()
    waiting_for_manual_phone = State()
    waiting_for_location = State()
    selecting_payment_method = State()
    waiting_for_payment_proof = State()

class FeedbackState(StatesGroup):
    waiting_for_comment = State()

class ChatState(StatesGroup):
    waiting_for_message = State()
    waiting_for_admin_reply = State()

class RegistrationState(StatesGroup):
    waiting_for_contact = State()
    # Holds referrer_code in data

dp = Dispatcher(storage=MemoryStorage())

# --- Helpers ---
def get_webapp_url():
    try:
        from users.models import SystemSettings
        setting = SystemSettings.objects.get(key='webapp_url')
        return setting.value
    except Exception:
        return "https://intracardiac-matutinal-caridad.ngrok-free.dev"

# --- Keyboards ---
def main_menu():
    url = get_webapp_url()
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐾 Mening hayvonlarim"), KeyboardButton(text="🛍 Mening buyurtmalarim")],
            [KeyboardButton(text="🏥 Qabulga yozilish"), KeyboardButton(text="💉 Vaksinalar")],
            [KeyboardButton(text="🛒 Pet Shop", web_app=WebAppInfo(url=url))], 
            [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="📞 Bog'lanish")]
        ],
        resize_keyboard=True
    )

def guest_menu():
    url = get_webapp_url()
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Ro'yxatdan o'tish")],
            [KeyboardButton(text="🛒 Pet Shop", web_app=WebAppInfo(url=url))],
            [KeyboardButton(text="📞 Kontaktlar")]
        ],
        resize_keyboard=True
    )

def confirm_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Ha, tasdiqlash")],
            [KeyboardButton(text="📞 Boshqa raqam kiritish")]
        ],
        resize_keyboard=True
    )

def contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def payment_method_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Karta orqali"), KeyboardButton(text="💵 Naqd pul")]
        ],
        resize_keyboard=True
    )

# --- Handlers ---

@dp.message(CommandStart())
async def command_start_handler(message: Message, command: CommandStart, state: FSMContext) -> None:
    telegram_id = str(message.from_user.id)
    
    # Handle Referral
    args = command.args
    referrer_code = None
    referrer = None
    
    if args:
        referrer_code = args
        try:
            referrer = await sync_to_async(Customer.objects.filter(referral_code=referrer_code).first)()
        except Exception as e:
            logging.error(f"Referral check error: {e}")

    try:
        # Check if user exists by telegram_id
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        
        # Already registered logic...
        # If user exists but has no referrer, could arguably link them?
        # But strict rules usually imply NEW users.
        await message.answer(f"Xush kelibsiz, {customer.name}!", reply_markup=main_menu())
        
    except Customer.DoesNotExist:
        # NEW USER FLOW
        # Store referrer in FSM for later use (Strict Registration)
        if referrer:
            await state.update_data(referrer_id=referrer.id)
            await message.answer(
                f"Assalomu alaykum! Sizni {referrer.name} taklif qildi.\n\n"
                "🎁 Sovg'a (Spin) olish uchun ro'yxatdan o'tishingiz kerak.\n"
                "Iltimos, pastdagi tugmani bosib telefon raqamingizni yuboring.",
                reply_markup=contact_keyboard()
            )
            await state.set_state(RegistrationState.waiting_for_contact)
        else:
            await message.answer(
                f"Assalomu alaykum! Vettakhirov klinikasining botiga xush kelibsiz.\n\n"
                "Bizning xizmatlardan to'liq foydalanish uchun ro'yxatdan o'tishingiz mumkin.",
                reply_markup=guest_menu()
            )

@dp.message(F.text == "📝 Ro'yxatdan o'tish")
async def register_handler(message: Message, state: FSMContext):
    await state.set_state(RegistrationState.waiting_for_contact)
    await message.answer(
        "Ro'yxatdan o'tish uchun telefon raqamingizni yuboring (+998...).",
        reply_markup=contact_keyboard()
    )

# Merged Contact Handler for both RegistrationState and OrderState if needed,
# or specific handler for RegistrationState
@dp.message(F.contact, RegistrationState.waiting_for_contact)
async def registration_contact_handler(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    
    # Normalize phone
    if not phone.startswith('+'):
        phone = '+' + phone

    # 1. Validation Rules (Uzbekistan only)
    if not re.match(r"^\+998\d{9}$", phone):
        await message.answer(
            "🚫 Faqat O'zbekiston raqamlari (+998...) bilan ro'yxatdan o'tish mumkin.\n"
            "Iltimos, to'g'ri raqamdan foydalaning."
        )
        return

    # 2. Prevention of Fraud (Unique Phone Check)
    exists = await sync_to_async(Customer.objects.filter(phone=phone).exists)()
    if exists:
        await message.answer("⚠️ Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        # Determine if we should clear state or let them try another number?
        # Let them try another number.
        return

    # 3. Create Customer
    telegram_id = str(message.from_user.id)
    
    try:
        # Check FSM for referrer
        data = await state.get_data()
        referrer_id = data.get('referrer_id')
        referrer = None
        
        if referrer_id:
            try:
                referrer = await sync_to_async(Customer.objects.get)(id=referrer_id)
            except Customer.DoesNotExist:
                pass

        customer = await sync_to_async(Customer.objects.create)(
            name=message.from_user.full_name,
            phone=phone,
            telegram_id=telegram_id,
            referred_by=referrer
        )
        
        # 4. Trigger Condition: Spin Awarding
        if referrer:
             # Check Global Limit
             settings_obj = await sync_to_async(GameSettings.get_settings)()
             limit = settings_obj.daily_referral_limit
             
             # Count Referrer's successful referrals TODAY
             # Assuming 'created_at' on Customer is when referral happened
             today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
             ref_count_today = await sync_to_async(Customer.objects.filter(
                 referred_by=referrer, 
                 created_at__gte=today_start
             ).count)()
             
             if ref_count_today <= limit:
                 # Award Spin
                 referrer.spins += 1
                 await sync_to_async(referrer.save)()
                 
                 # Notification
                 try:
                     if referrer.telegram_id:
                         await message.bot.send_message(
                             referrer.telegram_id,
                             f"🎉 Tabriklaymiz! Do'stingiz {customer.name} ro'yxatdan o'tdi.\n"
                             f"🎁 Sizga 1 ta bepul Spin qo'shildi!"
                         )
                 except Exception as e:
                     logging.error(f"Failed to notify referrer: {e}")
             else:
                 # Limit reached
                 pass 

        await message.answer("✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        await state.clear()
        
    except Exception as e:
        logging.error(f"Registration error: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")


# --- Existing Order/Other Handlers (Keep below or ensure no conflict) ---

@dp.message(F.contact)
# This is the "fallback" or "generic" contact handler if no specific state matches
# OR if OrderState matches. 
# Since we defined specific RegistrationState handler above, we need to handle generic/order cases here.
async def generic_contact_handler(message: Message, state: FSMContext):
    # This logic was originally handling everything. 
    # We should keep it for Order workflow or general updating.
    
    # ... (Keep existing generic logic for order flow if needed, but safer to rename generic_contact_handler)
    # Re-pasting original logic with slight adjustment to not conflict with RegistrationState
    
    current_state = await state.get_state()
    if current_state == RegistrationState.waiting_for_contact:
        # Should have been caught by specific handler, but just in case
        await registration_contact_handler(message, state)
        return
        
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    
    try:
        customer = await sync_to_async(Customer.objects.get)(phone=phone)
        customer.telegram_id = str(message.from_user.id)
        await sync_to_async(customer.save)()
        
        # Check for recent pending orders from Web App/Bot
        from shop.models import Order
        from datetime import timedelta
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)
        recent_order = await sync_to_async(Order.objects.filter(
            customer=customer, 
            status='NEW', 
            created_at__gte=ten_minutes_ago
        ).order_by('-created_at').first)()

        if recent_order:
            await state.set_state(OrderState.waiting_for_location)
            await state.update_data(order_id=recent_order.id)
            await message.answer(
                "✅ Telefon raqamingiz qabul qilindi!\n\n"
                "📍 Buyurtmangizni yakunlash uchun iltimos lokatsiyangizni yuboring:",
                reply_markup=location_keyboard()
            )
        else:
            await message.answer("✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_menu())
            
    except Customer.DoesNotExist:
        # If not in RegistrationState, maybe they just sent a contact randomly or during order without state?
        # Auto-create logic from before (but strict is preferred)
        
        # For now, replicate old logic but maybe warn or just accept?
        # Let's keep old relaxed logic for Order flow if state is not Registration
         # Check for recent order even if customer not in DB (web app user might have provided a name but no ID)
        from shop.models import Order
        from datetime import timedelta
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)
        recent_order = await sync_to_async(Order.objects.filter(
            customer_name__isnull=False,
            status='NEW',
            created_at__gte=ten_minutes_ago
        ).order_by('-created_at').first)()
        
        customer = await sync_to_async(Customer.objects.create)(
            name=message.from_user.full_name,
            phone=phone,
            telegram_id=str(message.from_user.id)
        )
        
        if recent_order:
            recent_order.customer = customer
            await sync_to_async(recent_order.save)()
            await state.set_state(OrderState.waiting_for_location)
            await state.update_data(order_id=recent_order.id)
            await message.answer(
                "✅ Telefon raqamingiz qabul qilindi!\n\n"
                "📍 Buyurtmangizni yakunlash uchun iltimos lokatsiyangizni yuboring:",
                reply_markup=location_keyboard()
            )
        else:
            # Maybe they just wanted to register via menu button?
            await message.answer("✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("order_confirm_phone_"))
async def order_confirm_phone_callback(callback: CallbackQuery, state: FSMContext):
    try:
        order_id = int(callback.data.split("_")[3])
        await state.update_data(order_id=order_id)
        await state.set_state(OrderState.waiting_for_location)
        
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "✅ Telefon raqamingiz tasdiqlandi!\n\n"
            "📍 Buyurtmangizni yakunlash uchun iltimos lokatsiyangizni yuboring:",
            reply_markup=location_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in order_confirm_phone_callback: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)

@dp.callback_query(F.data.startswith("order_change_phone_"))
async def order_change_phone_callback(callback: CallbackQuery, state: FSMContext):
    try:
        order_id = int(callback.data.split("_")[3])
        await state.update_data(order_id=order_id)
        await state.set_state(OrderState.waiting_for_phone)
        
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "📱 Iltimos, yangi telefon raqamingizni pastdagi tugmani bosib yuboring:",
            reply_markup=contact_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in order_change_phone_callback: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)

@dp.message(F.content_type == "web_app_data")
async def web_app_data_handler(message: Message, state: FSMContext):
    import json
    try:
        data = json.loads(message.web_app_data.data)
        if data.get('type') == 'order_created':
            order_id = data.get('order_id')
            await state.update_data(order_id=order_id)
            
            # Fetch order details from database
            from shop.models import Order, OrderItem
            try:
                order = await sync_to_async(Order.objects.get)(id=order_id)
                
                # Update customer name from Telegram
                telegram_name = message.from_user.full_name
                order.customer_name = telegram_name
                await sync_to_async(order.save)()
                
                items = await sync_to_async(list)(order.items.all())
                
                # Generate receipt
                receipt_text = "🧾 <b>Buyurtma cheki</b>\n\n"
                receipt_text += f"👤 Mijoz: {order.customer_name}\n\n"
                receipt_text += "<b>📦 Mahsulotlar:</b>\n"
                
                for item in items:
                    product = await sync_to_async(lambda: item.product)()
                    receipt_text += f"  • {product.name}\n"
                    receipt_text += f"    {item.quantity} x {item.price:,} so'm = {item.quantity * item.price:,} so'm\n"
                
                if order.delivery_fee:
                    subtotal = order.total_price - order.delivery_fee
                    receipt_text += f"\n📦 <b>Mahsulotlar:</b> {subtotal:,} so'm"
                    receipt_text += f"\n🚚 <b>Dastavka:</b> {order.delivery_fee:,} so'm"
                
                receipt_text += f"\n\n💰 <b>Jami:</b> {order.total_price:,} so'm"
                
                await message.answer(receipt_text, parse_mode="HTML")
                
                
                # Check if user has phone number
                telegram_id = str(message.from_user.id)
                try:
                    customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
                    if customer.phone:
                        # User has phone, ask if correct
                        await state.set_state(OrderState.confirm_existing_phone)
                        await message.answer(
                            f"Sizning raqamingiz: {customer.phone}\nAloqa uchun ushbu raqamni ishlataylikmi?",
                            reply_markup=confirm_phone_keyboard()
                        )
                    else:
                        # User exists but no phone (unlikely) or deleted phone
                        await state.set_state(OrderState.waiting_for_phone) # Strict button
                        await message.answer(
                            "📱 Iltimos, aloqa uchun tugma orqali telefon raqamingizni yuboring:",
                            reply_markup=contact_keyboard()
                        )
                except Customer.DoesNotExist:
                    # New user, ask for phone (Strict button)
                    await state.set_state(OrderState.waiting_for_phone)
                    await message.answer(
                        "📱 Iltimos, aloqa uchun telefon raqamingizni yuboring (tugma orqali):",
                        reply_markup=contact_keyboard()
                    )
                    
            except Order.DoesNotExist:
                await message.answer("❌ Buyurtma topilmadi. Iltimos, qaytadan urinib ko'ring.")
                
    except Exception as e:
        logging.error(f"Error processing web_app_data: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@dp.message(OrderState.confirm_existing_phone)
async def confirm_existing_phone_handler(message: Message, state: FSMContext):
    if message.text == "✅ Ha, tasdiqlash":
        await message.answer("✅ Telefon raqam tasdiqlandi!", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderState.waiting_for_location)
        await message.answer(
            "📍 Yetkazib berish uchun iltimos lokatsiyangizni yuboring:",
            reply_markup=location_keyboard()
        )
    elif message.text == "📞 Boshqa raqam kiritish":
        await state.set_state(OrderState.waiting_for_manual_phone)
        await message.answer(
            "📱 Iltimos, yangi telefon raqamingizni yuboring (yozing yoki tugmani bosing):",
            reply_markup=contact_keyboard()
        )
    else:
        await message.answer("Iltimos, tugmalardan birini tanlang.")

@dp.message(OrderState.waiting_for_manual_phone)
async def manual_phone_handler(message: Message, state: FSMContext):
    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text
        # Basic validation
        cleaned = phone.replace('+', '').replace(' ', '').replace('-', '')
        if not cleaned.isdigit() or len(cleaned) < 7:
            await message.answer("❌ Iltimos, to'g'ri telefon raqam kiriting (masalan: +998901234567).")
            return
    else:
        await message.answer("❌ Iltimos, telefon raqam yuboring.")
        return

    # Normalize
    phone = phone.replace(' ', '').replace('-', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    # Update DB
    telegram_id = str(message.from_user.id)
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        customer.phone = phone
        await sync_to_async(customer.save)()
    except Customer.DoesNotExist:
        await sync_to_async(Customer.objects.create)(
             name=message.from_user.full_name,
             phone=phone,
             telegram_id=telegram_id
        )

    await message.answer("✅ Telefon raqamingiz qabul qilindi!", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderState.waiting_for_location)
    await message.answer(
        "📍 Buyurtmangizni yakunlash uchun iltimos lokatsiyangizni yuboring:",
        reply_markup=location_keyboard()
    )

@dp.message(F.text, OrderState.waiting_for_phone)
async def reject_registration_text_handler(message: Message, state: FSMContext):
    await message.answer(
        "⚠️ Aloqa uchun <b>majburiy</b> ravishda pastdagi tugmani bosib telefon raqamingizni yuboring!",
        reply_markup=contact_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.contact, OrderState.waiting_for_phone)
async def registration_contact_handler_order(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    
    telegram_id = str(message.from_user.id)
    
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        customer.phone = phone
        await sync_to_async(customer.save)()
    except Customer.DoesNotExist:
        await sync_to_async(Customer.objects.create)(
            name=message.from_user.full_name,
            phone=phone,
            telegram_id=telegram_id
        )
    
    await message.answer("✅ Telefon raqamingiz qabul qilindi!", reply_markup=ReplyKeyboardRemove())
    
    await state.set_state(OrderState.waiting_for_location)
    await message.answer(
        "📍 Buyurtmangizni yakunlash uchun iltimos lokatsiyangizni yuboring:",
        reply_markup=location_keyboard()
    )


@dp.message(F.location, OrderState.waiting_for_location)
async def location_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')
    
    from shop.models import Order, OrderItem
    from users.models import SystemSettings
    
    try:
        order = await sync_to_async(Order.objects.get)(id=order_id)
        
        # Link Customer to Order
        telegram_id = str(message.from_user.id)
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        order.customer = customer
        
        order.latitude = message.location.latitude
        order.longitude = message.location.longitude
        await sync_to_async(order.save)()
        
        # Transition to Payment
        await state.set_state(OrderState.selecting_payment_method)
        await message.answer(
            "📍 Lokatsiya qabul qilindi!\n\n"
            "💳 Endi to'lov turini tanlang:",
            reply_markup=payment_method_keyboard()
        )

    except Order.DoesNotExist:
        await message.answer("Xatolik: Buyurtma topilmadi.")

async def notify_admin_helper(message, order_id, payment_method, proof_message=None):
    from shop.models import Order
    from users.models import SystemSettings
    from clinic.models import Customer
    from aiogram import Bot
    
    try:
        order = await sync_to_async(Order.objects.get)(id=order_id)
        admin_setting = await sync_to_async(SystemSettings.objects.get)(key='admin_telegram_id')
        admin_id = admin_setting.value
        
        # Details
        telegram_id = str(message.from_user.id)
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        phone = customer.phone
        
        items = await sync_to_async(list)(order.items.all())
        items_text = ""
        for item in items:
            product = await sync_to_async(lambda: item.product)()
            items_text += f"▫️ {product.name}\n   {item.quantity} x {item.price:,} so'm\n"

        from django.utils import timezone
        local_time = timezone.localtime(order.created_at)
        formatted_time = local_time.strftime("%d.%m.%Y %H:%M")

        msg_text = (
            f"🚨 <b>Yangi Buyurtma! #{order.id}</b>\n"
            f"🕒 <b>Vaqt:</b> {formatted_time}\n\n"
            f"👤 <b>Mijoz:</b> <a href='tg://user?id={telegram_id}'>{order.customer_name}</a>\n"
            f"📞 <b>Telefon:</b> {phone}\n"
            f"💰 <b>Jami:</b> {order.total_price:,} so'm\n"
            f"💳 <b>To'lov:</b> {payment_method}\n\n"
            f"📦 <b>Mahsulotlar:</b>\n{items_text}\n"
            f"📍 <b>Lokatsiya:</b> Quyida biriktirilgan."
        )

        # Approval Keyboard
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Buyurtmani Tasdiqlash", callback_data=f"approve_order_{order.id}")]]
        )

        bot_token = message.bot.token
        bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        if proof_message:
             photo_id = proof_message.photo[-1].file_id
             await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=msg_text, reply_markup=keyboard)
        else:
             await bot.send_message(chat_id=admin_id, text=msg_text, reply_markup=keyboard)

        if order.latitude and order.longitude:
             await bot.send_location(chat_id=admin_id, latitude=order.latitude, longitude=order.longitude)
        
        await bot.session.close()

    except Exception as e:
        logging.error(f"Notify error: {e}")

@dp.callback_query(F.data.startswith("approve_order_"))
async def approve_order_handler(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split("_")[2])
        from shop.models import Order
        
        order = await sync_to_async(Order.objects.get)(id=order_id)
        order.status = 'PREPARING'
        await sync_to_async(order.save)()
        
        customer = await sync_to_async(lambda: order.customer)()
        if customer and customer.telegram_id:
             await callback.bot.send_message(
                 customer.telegram_id, 
                 f"✅ <b>Buyurtmangiz #{order_id} tasdiqlandi!</b>\n\nTez orada kuryerimiz buyurtmangizni yetkazib boradi. 😊", 
                 parse_mode="HTML"
             )
        
        await callback.message.edit_reply_markup(reply_markup=None) # Remove button
        await callback.answer("✅ Buyurtma tasdiqlandi va mijozga xabar yuborildi.")
    except Exception as e:
        await callback.answer(f"Xatolik: {e}", show_alert=True)

@dp.message(OrderState.selecting_payment_method)
async def payment_method_handler(message: Message, state: FSMContext):
    if message.text not in ["💵 Naqd pul", "💳 Karta orqali"]:
        await message.answer("Iltimos, tugmalardan birini tanlang.")
        return

    data = await state.get_data()
    order_id = data.get('order_id')
    from shop.models import Order

    if message.text == "💵 Naqd pul":
        # Save to DB
        order = await sync_to_async(Order.objects.get)(id=order_id)
        order.payment_method = 'CASH'
        await sync_to_async(order.save)()

        # Notify Admin Logic
        await notify_admin_helper(message, order_id, "Naqd pul")
        
        await message.answer(
            "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
            "⏳ Hozirda buyurtmangiz <b>admin tomonidan ko'rib chiqilmoqda</b>.\n"
            "Tasdiqlanishi bilan sizga xabar yuboramiz.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        await state.clear()
        
    elif message.text == "💳 Karta orqali":
        # Save to DB
        order = await sync_to_async(Order.objects.get)(id=order_id)
        order.payment_method = 'CARD'
        await sync_to_async(order.save)()

        await state.set_state(OrderState.waiting_for_payment_proof)
        await message.answer(
            "💳 Iltimos, to'lovni quyidagi kartaga o'tkazing:\n\n"
            "<b>8600 0000 0000 0000</b> (Egamqulov O.)\n\n"
            "To'lov qilganingizdan so'ng, chek rasmini (skrinshot) shu yerga yuboring.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(OrderState.waiting_for_payment_proof, F.photo)
async def payment_proof_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Optional: Save photo to Order.payment_proof
    # For now we just notify admin with the photo link/id
    # To truly save to Django ImageField, we'd need to download it.
    
    await notify_admin_helper(message, order_id, "Karta orqali", proof_message=message)
    
    await message.answer(
        "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
        "⏳ Buyurtmangiz <b>admin tomonidan ko'rib chiqilmoqda</b>.\n"
        "Tasdiqlanishi bilan sizga xabar yuboramiz.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await state.clear()

@dp.message(F.text == "🔗 Referal")
async def referral_handler(message: Message):
    telegram_id = str(message.from_user.id)
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        
        # Ensure referral code exists
        if not customer.referral_code:
            import uuid
            customer.referral_code = str(uuid.uuid4())[:8].upper()
            await sync_to_async(customer.save)()
            
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        
        ref_link = f"https://t.me/{bot_username}?start={customer.referral_code}"
        
        text = (
            f"🎉 <b>Do'stlarni taklif qiling va Spin yutib oling!</b>\n\n"
            f"Sizning referal havolangiz:\n"
            f"<code>{ref_link}</code>\n\n"
            f"Har bir taklif qilingan do'stingiz uchun 1 ta bepul Spin beriladi! 🎰"
        )
        
        # Share URL
        from urllib.parse import quote
        share_text = f"Assalomu alaykum! {customer.name} sizni Vettakhirov klinikasining botiga taklif qilmoqda. Ro'yxatdan o'ting va sovg'alar yutib oling!"
        share_url = f"https://t.me/share/url?url={ref_link}&text={quote(share_text)}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⤴️ Do'stlarga ulashish", url=share_url)]
        ])
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        
    except Customer.DoesNotExist:
        await message.answer("Referal tizimidan foydalanish uchun avval ro'yxatdan o'ting.", reply_markup=guest_menu())

@dp.message(F.text == "🐾 Mening hayvonlarim")
async def my_pets_handler(message: Message):
    telegram_id = str(message.from_user.id)
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        pets = await sync_to_async(list)(customer.pets.all())
        
        if not pets:
            await message.answer("Sizda ro'yxatga olingan hayvonlar yo'q.")
        else:
            for pet in pets:
                response = f"🐶 <b>{pet.name}</b> ({pet.species})\nℹ️ Zoti: {pet.breed}\n🎂 Yoshi: {pet.age} yosh\n\n"
                
                # Inline button for history
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📜 Tibbiy tarix", callback_data=f"history_{pet.id}")]
                ])
                await message.answer(response, reply_markup=kb, parse_mode="HTML")
    except Customer.DoesNotExist:
        await message.answer("Iltimos, avval ro'yxatdan o'ting", reply_markup=guest_menu())

@dp.callback_query(F.data.startswith("history_"))
async def pet_history_handler(callback: CallbackQuery):
    pet_id = int(callback.data.split("_")[1])
    try:
        from clinic.models import MedicalRecord
        pet = await sync_to_async(Pet.objects.get)(id=pet_id)
        records = await sync_to_async(list)(MedicalRecord.objects.filter(pet=pet).order_by('-date')[:5])
        
        if not records:
            await callback.answer("📜 Tibbiy tarix hali bo'sh.", show_alert=True)
            return

        history_text = f"📜 <b>{pet.name} - Tibbiy tarix:</b>\n\n"
        for rec in records:
            date_str = rec.date.strftime("%d.%m.%Y")
            history_text += f"📅 {date_str} - <b>{rec.get_record_type_display()}</b>\n"
            if rec.diagnosis:
                history_text += f"🩺 Diagnoz: {rec.diagnosis}\n"
            if rec.treatment:
                history_text += f"💊 Muolaja: {rec.treatment}\n"
            history_text += f"📝 Izoh: {rec.description}\n"
            history_text += "---" * 5 + "\n"
        
        await callback.message.answer(history_text, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logging.error(f"Pet history error: {e}")
        await callback.answer("Xatolik yuz berdi")

@dp.message(F.text == "📞 Bog'lanish")
async def contact_handler(message: Message):
    text = (
        "📞 <b>Biz bilan bog'lanish:</b>\n\n"
        "📍 Manzil: Toshkent sh., Mirzo Ulug'bek tumani\n"
        "☎️ Telefon: +998 90 123 45 67\n"
        "🌐 Sayt: vet-clinic.uz\n\n"
        "Bot orqali xabar yozishingiz ham mumkin. Savolingiz bo'lsa, quyidagi tugmani bosing:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Admin bilan bog'lanish", callback_data="chat_admin")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "chat_admin")
async def chat_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatState.waiting_for_message)
    await callback.message.answer("⌨️ Savolingizni yoki xabaringizni yozib yuboring. Shifokorlarimiz sizga tez orada javob qaytarishadi.")
    await callback.answer()

@dp.message(ChatState.waiting_for_message)
async def chat_admin_message(message: Message, state: FSMContext):
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "562723145")
    
    # Forward to admin
    try:
        from_user = message.from_user.full_name
        user_id = message.from_user.id
        
        admin_msg = (
            f"🆘 <b>Yangi xabar!</b>\n\n"
            f"👤 Mijoz: {from_user} (ID: {user_id})\n"
            f"💬 Xabar: {message.text}"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Javob berish", callback_data=f"reply_to_{user_id}")]
        ])
        
        await message.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, reply_markup=kb, parse_mode="HTML")
        await message.answer("✅ Xabaringiz yuborildi. Tez orada javob qaytaramiz! 😊", reply_markup=main_menu())
        await state.clear()
    except Exception as e:
        logging.error(f"Support chat error: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

@dp.callback_query(F.data.startswith("reply_to_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    try:
        user_id = callback.data.split("_")[2]
        await state.update_data(reply_to_user_id=user_id)
        await state.set_state(ChatState.waiting_for_admin_reply)
        await callback.message.answer(f"⌨️ ID {user_id} li mijozga javobingizni yozing:")
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Xatolik: {e}")

@dp.message(ChatState.waiting_for_admin_reply)
async def admin_reply_send(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('reply_to_user_id')
    
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"💬 <b>Admin javobi:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        await message.answer("✅ Javobingiz yuborildi.")
        await state.clear()
    except Exception as e:
        logging.error(f"Admin reply error: {e}")
        await message.answer(f"❌ Xabar yuborishda xatolik: {e}")

@dp.message(F.text == "🛍 Mening buyurtmalarim")
async def my_orders_handler(message: Message):
    from shop.models import Order
    from clinic.models import Customer
    
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=str(message.from_user.id))
        orders = await sync_to_async(lambda: list(Order.objects.filter(customer=customer).order_by('-created_at')[:5]))()
        
        if not orders:
            await message.answer("📭 Sizda hali buyurtmalar yo'q.")
            return
            
        text = "🛍 <b>Oxirgi 5 ta buyurtmangiz:</b>\n\n"
        for order in orders:
            status_map = {
                'NEW': '🆕 Yangi',
                'PREPARING': '👨‍🍳 Tayyorlanmoqda',
                'ON_WAY': '🚚 Yo\'lda',
                'DELIVERED': '✅ Yetkazildi',
                'CANCELLED': '❌ Bekor qilindi'
            }
            status = status_map.get(order.status, order.status)
            text += f"🆔 <b>Order #{order.id}</b>\n"
            text += f"📅 Sana: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            text += f"💰 Summa: {order.total_price:,} so'm\n"
            text += f"📊 Holat: {status}\n\n"
            
        await message.answer(text, parse_mode="HTML")
    except Customer.DoesNotExist:
        await message.answer("👨‍⚕️ Buyurtmalaringizni ko'rish uchun avval ro'yxatdan o'ting.")

@dp.message(F.text == "💉 Vaksinalar")
async def vaccines_handler(message: Message):
    telegram_id = str(message.from_user.id)
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        pets = await sync_to_async(list)(customer.pets.all())
        
        if not pets:
            await message.answer("Hayvonlar topilmadi.")
            return

        has_info = False
        for pet in pets:
            vaccines = await sync_to_async(list)(pet.vaccines.all())
            if vaccines:
                has_info = True
                msg = f"<b>{pet.name} uchun vaksinalar:</b>\n"
                for vac in vaccines:
                    msg += f"- {vac.vaccine_name}: {vac.next_date} (Keyingi)\n"
                await message.answer(msg)
        
        if not has_info:
            await message.answer("Hozircha vaksina ma'lumotlari mavjud emas.")
    except Customer.DoesNotExist:
        await message.answer("Iltimos, avval ro'yxatdan o'ting", reply_markup=guest_menu())

# --- Booking System ---
@dp.message(F.text == "🏥 Qabulga yozilish")
async def start_booking(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=telegram_id)
        pets = await sync_to_async(list)(customer.pets.all())

        if not pets:
            await message.answer("Sizda ro'yxatga olingan hayvonlar yo'q. Qabulga yozilish uchun avval klinikaga tashrif buyuring va hayvoningizni ro'yxatga qo'shing.")
            return

        await state.update_data(pets=pets)
        
        kb = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
        # Create buttons for pets
        rows = []
        for pet in pets:
            rows.append([KeyboardButton(text=pet.name)])
        kb.keyboard = rows
        
        await message.answer("Qaysi hayvon uchun qabulga yozilmoqchisiz?", reply_markup=kb)
        await state.set_state(BookingState.selecting_pet)

    except Customer.DoesNotExist:
        await message.answer("Iltimos, avval ro'yxatdan o'ting", reply_markup=guest_menu())

@dp.message(BookingState.selecting_pet)
async def booking_select_pet(message: Message, state: FSMContext):
    data = await state.get_data()
    pets = data.get('pets', [])
    selected_pet = next((p for p in pets if p.name == message.text), None)
    
    if not selected_pet:
        await message.answer("Iltimos, ro'yxatdan hayvon tanlang.")
        return

    await state.update_data(selected_pet_id=selected_pet.id)
    
    purposes = [
        [KeyboardButton(text="Ko'rik (Konsultatsiya)")],
        [KeyboardButton(text="Emlash (Vaksina)")],
        [KeyboardButton(text="Davolash")],
        [KeyboardButton(text="Boshqa")]
    ]
    kb = ReplyKeyboardMarkup(keyboard=purposes, resize_keyboard=True)
    
    await message.answer("Tashrif maqsadi nima?", reply_markup=kb)
    await state.set_state(BookingState.selecting_purpose)

@dp.message(BookingState.selecting_purpose)
async def booking_select_purpose(message: Message, state: FSMContext):
    purpose = message.text
    data = await state.get_data()
    pet_id = data.get('selected_pet_id')
    
    # Save booking request logic here (e.g. create Visit with status 'WAITING')
    # Use sync_to_async
    try:
        pet = await sync_to_async(Pet.objects.get)(id=pet_id)
        visit = await sync_to_async(Visit.objects.create)(
            pet=pet,
            purpose=purpose,
            status='WAITING'
        )
        
        await message.answer(f"✅ Qabulga so'rov yuborildi!\n\nSiz bilan tez orada bog'lanamiz.", reply_markup=main_menu())
        await state.clear()
        
        # Notify Admin
        ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "562723145")
        await message.bot.send_message(
            ADMIN_CHAT_ID,
            f"📝 <b>Yangi Qabul So'rovi!</b>\n\n"
            f"👤 Mijoz: {message.from_user.full_name}\n"
            f"🐶 Hayvon: {pet.name} ({pet.species})\n"
            f"📌 Maqsad: {purpose}\n"
            f"📞 Tel: {pet.customer.phone}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Booking error: {e}")
        await message.answer("Xatolik yuz berdi.")

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
