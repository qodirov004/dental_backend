from django.db import models
from clinic.models import Customer
from django.utils import timezone

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partial'),
        ('UNPAID', 'Unpaid'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer.name}"

class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('CLICK', 'Click'),
        ('PAYME', 'Payme'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    bonus_used = models.DecimalField(max_digits=20, decimal_places=2, default=0, help_text="Amount paid via bonuses")
    cashback_earned = models.DecimalField(max_digits=20, decimal_places=2, default=0, help_text="New bonus earned from this payment")
    date = models.DateTimeField(default=timezone.now)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='CASH')

    def __str__(self):
        return f"Payment #{self.id} for Invoice #{self.invoice.id} ({self.method})"

class InvoiceItem(models.Model):
    """
    Detailed line item for an invoice (Service, Product, or Consumable).
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    total_price = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Optional links to source
    # product = models.ForeignKey('shop.Product', ...) # Can add later if needed
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} x{self.quantity}"
