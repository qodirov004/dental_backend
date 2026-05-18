from decimal import Decimal
from rest_framework import serializers
from .models import Product, Order, OrderItem, Category, Supplier
from clinic.models import Customer
from games.models import GameSession
from django.utils import timezone

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    items_input = serializers.ListField(child=serializers.DictField(), write_only=True)
    client_name = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    telegram_id = serializers.CharField(write_only=True, required=False)
    coupon_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_name', 'client_name', 'customer_phone', 'total_price', 'delivery_fee', 'status', 'created_at', 'items', 'items_input', 'latitude', 'longitude', 'source', 'telegram_id', 'payment_method', 'payment_proof', 'bonus_credited', 'coupon_code']

    def get_client_name(self, obj):
        if obj.customer:
            return obj.customer.name
        return obj.customer_name or "Mijozsiz"

    def create(self, validated_data):
        items_data = validated_data.pop('items_input')
        telegram_id = validated_data.pop('telegram_id', None)
        coupon_code = validated_data.pop('coupon_code', None)
        delivery_fee = validated_data.get('delivery_fee', 0)
        source = validated_data.get('source', 'POS')
        
        # Validate Coupon first if exists
        game_session = None
        if coupon_code:
            try:
                game_session = GameSession.objects.select_related('prize').get(coupon_code=coupon_code)
                if game_session.is_used:
                    raise serializers.ValidationError({"coupon_code": "Ushbu kupon allaqachon ishlatilgan."})
            except GameSession.DoesNotExist:
                 raise serializers.ValidationError({"coupon_code": "Kupon kodi noto'g'ri."})

        
        # Default to user's requested ID for testing/web app
        # if not telegram_id and source == 'TELEGRAM_BOT':
        #     telegram_id = '7102675435'

        # Look up customer by telegram_id if not already provided
        if telegram_id and not validated_data.get('customer'):
            try:
                customer = Customer.objects.get(telegram_id=str(telegram_id))
                validated_data['customer'] = customer
            except Customer.DoesNotExist:
                pass

        order = Order.objects.create(**validated_data)
        
        total_price = Decimal(str(delivery_fee))
        for item in items_data:
            product_id = item.get('product_id') or item.get('product')
            product = Product.objects.get(id=product_id)
            quantity = item['quantity']
            
            # Check stock
            if product.stock < quantity:
                raise serializers.ValidationError(f"Not enough stock for {product.name}")
            
            # Update stock
            product.stock -= quantity
            product.save()
            
            # Create OrderItem
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price
            )
            total_price += (product.price * quantity)
            
        # Apply Coupon Discount
        if game_session:
            prize_name = game_session.prize.name.lower()
            
            # Simple Logic for MVP
            if '5%' in prize_name:
                discount_amount = total_price * Decimal('0.05')
                total_price -= discount_amount
            elif '10%' in prize_name:
                discount_amount = total_price * Decimal('0.10')
                total_price -= discount_amount
            elif 'bepul yetkazib berish' in prize_name or 'free delivery' in prize_name:
                delivery_fee = 0 # This won't work perfectly as delivery_fee is already saved in validated_data/order
                # So we update the order object
                order.delivery_fee = 0
                # And re-calc total if total includes delivery fee (in this logic total_price is just items sum)
            
            # Note: total_price currently is ITEM TOTAL. Order total usually is Items + Delivery.
            # But the logic below sets order.total_price. Let's assume order.total_price is just items sum according to previous code
            # Wait, previous code: order.total_price = total_price. And delivery_fee is separate on model. 
            # Usually strict E-commerce separates subtotal and total.
            # Let's verify OrderPage.tsx calc: total = subtotal + DELIVERY_PRICE.
            # But server side creates order. Server side should store TOTAL payable?
            # Model has total_price and delivery_fee.
            # Let's assume total_price should be FINAL price including delivery?
            # Looking at previous create method:
            # total_price = Decimal(str(delivery_fee))  <-- Starts with delivery fee!
            # So yes, total_price INCLUDES delivery fee.
            
            # Re-evaluating discount logic with delivery fee baked in total_price start
            
            # Mark coupon as used
            game_session.is_used = True
            game_session.used_at = timezone.now()
            game_session.save()
            order.coupon_code = coupon_code

        # If we applied Free Delivery, we need to correct the total_price calculation logic
        # Current flow:
        # total_price initialized with delivery_fee (Decimal(str(delivery_fee)))
        # loops items and adds to total_price.
        # So if free delivery, we should have initialized with 0 OR subtract delivery_fee now.
        if game_session and ('bepul yetkazib berish' in game_session.prize.name.lower() or 'free delivery' in game_session.prize.name.lower()):
             total_price -= Decimal(str(validated_data.get('delivery_fee', 0)))

        order.total_price = total_price
        order.save()
        return order
