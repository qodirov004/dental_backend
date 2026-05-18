from rest_framework import serializers
from .models import Invoice, Payment, InvoiceItem

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'title', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['total_price']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    pet_name = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_debt = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'customer', 'customer_name', 'pet_name', 'total_amount', 'status', 'created_at', 'items', 'payments', 'paid_amount', 'remaining_debt']
    
    def get_pet_name(self, obj):
        if obj.customer and obj.customer.pets.exists():
            return obj.customer.pets.first().name
        return "N/A"

    def get_paid_amount(self, obj):
        return sum(p.amount for p in obj.payments.all())

    def get_remaining_debt(self, obj):
        return obj.total_amount - self.get_paid_amount(obj)

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(**validated_data)
        
        calculated_total = 0
        for item_data in items_data:
            # Create item
            item = InvoiceItem.objects.create(invoice=invoice, **item_data)
            calculated_total += item.total_price
            
        # Optional: Auto-update total_amount from items if not provided or to ensure accuracy
        # invoice.total_amount = calculated_total
        # invoice.save()
        
        return invoice
