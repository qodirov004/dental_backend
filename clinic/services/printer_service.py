from django.utils import timezone

class QueuePrintService:
    """
    Navbat chekini PrintJob orqali bazaga qo'shadi.
    dental_print_agent.py agenti uni oladi va GEZHI printerda chop etadi.
    """
    
    def print_ticket(self, visit):
        """Ma'lumotlarni yig'adi va bazadagi navbatga (PrintJob) qo'shadi."""
        from ..models import PrintJob
        try:
            # Bemor ismi (customer nomi)
            patient_name = "Noma'lum"
            if visit.pet:
                if visit.pet.customer:
                    patient_name = visit.pet.customer.name
                else:
                    patient_name = visit.pet.name
            
            # Shifokor ismi
            doctor_name = "Ixtiyoriy"
            if visit.veterinarian:
                full_name = visit.veterinarian.get_full_name()
                doctor_name = full_name if full_name.strip() else visit.veterinarian.username

            data = {
                'q': visit.queue_number or "---",
                'd': doctor_name,
                'p': patient_name,
                't': timezone.now().strftime("%d.%m.%Y %H:%M")
            }
            
            # Vazifani bazaga saqlaymiz - agent uni oladi
            PrintJob.objects.create(data=data)
            return True
        except Exception as e:
            print(f"QueuePrintService Error: {e}")
            return False

