from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import Payment, Invoice

@receiver(post_save, sender=Payment)
def update_invoice_status(sender, instance, **kwargs):
    """Update Invoice status when a payment is made"""
    invoice = instance.invoice
    total_paid = invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
    
    if total_paid >= invoice.total_amount:
        invoice.status = 'PAID'
    elif total_paid > 0:
        invoice.status = 'PARTIAL'
    else:
        invoice.status = 'UNPAID'
        
    invoice.save()
