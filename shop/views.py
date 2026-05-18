from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from .models import Product, Order, OrderItem, Category, Supplier
from .serializers import ProductSerializer, OrderSerializer, CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ['category', 'name']
    search_fields = ['name', 'description']

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """Get list of expiring batches"""
        from django.utils import timezone
        from .models import ProductBatch
        from datetime import timedelta
        
        today = timezone.now().date()
        threshold_date = today + timedelta(days=30) # Default 30 days
        
        expiring_batches = ProductBatch.objects.filter(
            expiry_date__lte=threshold_date,
            quantity__gt=0
        ).select_related('product').order_by('expiry_date')
        
        data = []
        for batch in expiring_batches:
            days_left = (batch.expiry_date - today).days
            data.append({
                "id": batch.id,
                "product_name": batch.product.name,
                "batch_id": batch.batch_id,
                "expiry_date": batch.expiry_date,
                "days_left": days_left,
                "quantity": batch.quantity,
                "status": "CRITICAL" if days_left <= 7 else "WARNING" if days_left <= 15 else "NOTICE"
            })
            
        return Response(data)

class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    from .serializers import SupplierSerializer
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    from django_filters.rest_framework import DjangoFilterBackend
    from rest_framework import filters
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'customer', 'source']

    @action(detail=True, methods=['get'])
    def download_receipt(self, request, pk=None):
        """Generate and download PDF receipt"""
        from utils.pdf_generator import generate_order_receipt_pdf, pdf_response
        
        order = self.get_object()
        try:
            pdf_file = generate_order_receipt_pdf(order)
            inline = request.query_params.get('inline', 'false').lower() == 'true'
            return pdf_response(pdf_file, f'order_{order.id}_receipt.pdf', inline=inline)
        except Exception as e:
            return Response(
                {"error": f"PDF yaratishda xatolik: {str(e)}"},
                status=500
            )
    
    def create(self, request, *args, **kwargs):
        from django.db import transaction
        from rest_framework import status
        
        items_data = request.data.get('items', [])
        
        # Validate stock availability before creating order
        for item_data in items_data:
            product_id = item_data.get('product_id') or item_data.get('product')
            quantity = item_data.get('quantity', 1)
            
            try:
                product = Product.objects.get(id=product_id)
                if product.stock < quantity:
                    return Response({
                        "error": f"{product.name} uchun yetarli mahsulot yo'q. Qolgan: {product.stock}, Kerak: {quantity}"
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Product.DoesNotExist:
                return Response({
                    "error": f"Mahsulot topilmadi (ID: {product_id})"
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Create order atomically
        with transaction.atomic():
            # Create order
            response = super().create(request, *args, **kwargs)
            
            if response.status_code == 201:
                order = Order.objects.get(id=response.data['id'])
                
                # Notify customer if it's a bot order
                if order.source == 'TELEGRAM_BOT':
                     self.notify_customer(order)
            
            return response

    def notify_customer(self, order):
        """Send receipt and phone request to customer via Bot API"""
        from asgiref.sync import async_to_sync
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        import os
        
        # Get telegram_id from customer or default used in serializer
        telegram_id = None
        if order.customer:
            telegram_id = order.customer.telegram_id
        
        # If still no ID, we check the default one specified for testing
        if not telegram_id:
            telegram_id = "7102675435" # Default for testing

        try:
            items = order.items.all()
            receipt_text = "🧾 <b>Buyurtma cheki</b>\n\n"
            receipt_text += f"👤 Mijoz: {order.customer_name or 'Hurmatli mijoz'}\n\n"
            receipt_text += "<b>📦 Mahsulotlar:</b>\n"
            
            for item in items:
                receipt_text += f"  • {item.product.name}\n"
                receipt_text += f"    {item.quantity} x {item.price:,} so'm = {item.quantity * item.price:,} so'm\n"
            
            if order.delivery_fee:
                subtotal = order.total_price - order.delivery_fee
                receipt_text += f"\n📦 <b>Jami mahsulot:</b> {subtotal:,} so'm"
                receipt_text += f"\n🚚 <b>Dastavka:</b> {order.delivery_fee:,} so'm"
            
            receipt_text += f"\n\n💰 <b>Jami summa:</b> {order.total_price:,} so'm"
            
            async def send_notification():
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
                bot_token = os.getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0")
                
                async with Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
                    # Check if customer has phone
                    customer_phone = None
                    if order.customer and order.customer.phone:
                        customer_phone = order.customer.phone
                    
                    if customer_phone:
                        msg_text = (
                            f"{receipt_text}\n\n"
                            f"📞 Aloqa uchun <b>{customer_phone}</b> raqamingiz qolsinmi yoki boshqa raqam berasizmi?"
                        )
                        kb = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Shu raqam qolsin", callback_data=f"order_confirm_phone_{order.id}")],
                                [InlineKeyboardButton(text="📞 Boshqa raqam berish", callback_data=f"order_change_phone_{order.id}")]
                            ]
                        )
                        await bot.send_message(chat_id=telegram_id, text=msg_text, reply_markup=kb)
                    else:
                        msg_text = (
                            f"{receipt_text}\n\n"
                            "📱 Iltimos, buyurtmani yakunlash uchun pastdagi tugmani bosib <b>telefon raqamingizni yuboring</b>."
                        )
                        kb = ReplyKeyboardMarkup(
                            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
                            resize_keyboard=True,
                            one_time_keyboard=True
                        )
                        await bot.send_message(chat_id=telegram_id, text=msg_text, reply_markup=kb)

            async_to_sync(send_notification)()
            
        except Exception as e:
            print(f"Error notifying customer: {e}")

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total_sales = Order.objects.aggregate(total=Sum('total_price'))['total'] or 0
        order_count = Order.objects.count()
        
        # Category stats
        category_stats = OrderItem.objects.values('product__category').annotate(
            total_value=Sum('price'),
            total_quantity=Sum('quantity')
        ).order_by('-total_value')

        # Weekly dynamics (last 7 entries for demo)
        weekly_dynamics = Order.objects.order_by('-created_at')[:7]
        
        return Response({
            "total_sales": total_sales,
            "order_count": order_count,
            "category_stats": category_stats,
            "total_categories": Category.objects.count(),
            "recent_orders": OrderSerializer(weekly_dynamics, many=True).data
        })

    @action(detail=True, methods=['post'], url_path='notify-admin')
    def notify_admin(self, request, pk=None):
        from asgiref.sync import async_to_sync
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from users.models import SystemSettings
        import os
        
        order = self.get_object()
        
        try:
            admin_setting = SystemSettings.objects.get(key='admin_telegram_id')
            admin_id = admin_setting.value
            
            items = order.items.all()
            items_text = ""
            for item in items:
                 items_text += f"▫️ {item.product.name}\n   {item.quantity} x {item.price:,} so'm\n"
            
            customer_name = order.customer_name
            phone = "Topilmadi"
            telegram_id = None
            if order.customer:
                 phone = order.customer.phone
                 telegram_id = order.customer.telegram_id
            
            if telegram_id:
                name_line = f"👤 <b>Mijoz:</b> <a href='tg://user?id={telegram_id}'>{customer_name}</a>\n"
            else:
                name_line = f"👤 <b>Mijoz:</b> {customer_name}\n"
            
            from django.utils import timezone
            local_time = timezone.localtime(order.created_at)
            formatted_time = local_time.strftime("%d.%m.%Y %H:%M")

            msg_text = (
                f"🚨 <b>Qayta yuborilgan Buyurtma! #{order.id}</b>\n"
                f"🕒 <b>Vaqt:</b> {formatted_time}\n\n"
                f"{name_line}"
                f"📞 <b>Telefon:</b> {phone}\n"
                f"💰 <b>Jami:</b> {order.total_price:,} so'm\n\n"
                f"📦 <b>Mahsulotlar:</b>\n{items_text}\n"
                f"📍 <b>Lokatsiya:</b> Quyida biriktirilgan."
            )
            
            async def send_notification():
                 # Use fallback token if env var missing, matching bot/main.py
                 bot_token = os.getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0")
                 
                 async with Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
                      await bot.send_message(chat_id=admin_id, text=msg_text)
                      if order.latitude and order.longitude:
                           await bot.send_location(chat_id=admin_id, latitude=order.latitude, longitude=order.longitude)

            async_to_sync(send_notification)()
            
            return Response({"status": "success"})
            
        except Exception as e:
            print(f"Error in notify_admin: {e}")
            import traceback
            traceback.print_exc()
            return Response({"status": "error", "message": str(e)}, status=500)
