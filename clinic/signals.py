from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Visit
from .services.printer_service import QueuePrintService

@receiver(post_save, sender=Visit)
def auto_print_ticket(sender, instance, created, **kwargs):
    """
    Yangi navbat yaratilganda avtomatik chek chiqarish.
    Faqat 'WAITING' (Kutilmoqda) statusidagi yangi yozuvlar uchun.
    """
    if created and instance.status == 'WAITING':
        try:
            service = QueuePrintService()
            service.print_ticket(instance)
        except Exception as e:
            # Log xatolikni yozib boradi, lekin dastur to'xtab qolmaydi
            print(f"Auto-print Signal Error: {e}")
