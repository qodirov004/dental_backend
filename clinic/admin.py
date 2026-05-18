from django.contrib import admin
from .models import Customer, Pet, MedicalRecord, Visit, VaccineSchedule

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'created_at')
    search_fields = ('name', 'phone')

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'breed', 'customer', 'age', 'gender')
    list_filter = ('species', 'gender')
    search_fields = ('name', 'customer__name')

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('pet', 'record_type', 'date', 'veterinarian')
    list_filter = ('record_type', 'date')
    search_fields = ('pet__name', 'pet__customer__name')

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('queue_number', 'pet', 'purpose', 'status', 'arrived_at')
    list_filter = ('status', 'arrived_at')
    actions = ['reprint_ticket']

    def reprint_ticket(self, request, queryset):
        from .services.printer_service import QueuePrintService
        service = QueuePrintService()
        for visit in queryset:
            service.print_ticket(visit)
        self.message_user(request, f"{queryset.count()} ta chek chop etishga yuborildi.")
    reprint_ticket.short_description = "Chekni qayta chop etish"

@admin.register(VaccineSchedule)
class VaccineScheduleAdmin(admin.ModelAdmin):
    list_display = ('pet', 'vaccine_name', 'next_date', 'last_date')
    list_filter = ('vaccine_name', 'next_date')

