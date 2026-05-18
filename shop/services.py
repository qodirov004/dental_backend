from django.db import transaction
from django.db.models import F
from .models import Product, ProductBatch, ConsumableSet

class InventoryService:
    @staticmethod
    @transaction.atomic
    def deduct_consumables_for_set(consumable_set_id):
        try:
            c_set = ConsumableSet.objects.get(id=consumable_set_id)
            for item in c_set.items.all():
                InventoryService.deduct_product_stock(item.product, item.quantity)
        except ConsumableSet.DoesNotExist:
            pass

    @staticmethod
    @transaction.atomic
    def deduct_product_stock(product, quantity):
        """
        Deduct stock from Product (total) and Productbatches (FIFO).
        """
        # 1. Deduct from total stock
        # We use F() to avoid race conditions on total stock, but we need current value for checks
        product.refresh_from_db()
        if product.stock < quantity:
            # Decide: Allow negative or raise error? 
            # For clinics, usually we allow negative tracking if emergency, but let's log it.
            # Here we just subtract, it might go negative.
            pass
        
        product.stock = F('stock') - quantity
        product.save()
        
        # 2. Deduct from Batches (FIFO by expiry_date)
        remaining_qty = quantity
        batches = ProductBatch.objects.filter(product=product, quantity__gt=0).order_by('expiry_date')
        
        for batch in batches:
            if remaining_qty <= 0:
                break
                
            if batch.quantity >= remaining_qty:
                batch.quantity = F('quantity') - remaining_qty
                batch.save()
                remaining_qty = 0
            else:
                # batch has less than needed, take all
                taken = batch.quantity
                batch.quantity = 0
                batch.save()
                remaining_qty -= taken
                
        # If remaining_qty > 0, it means we ran out of batches but total stock was deducted (or went negative)
        # This matches real world: sometimes we use stock that wasn't properly entered in a batch.
