from django.db import models
from django.utils import timezone
from django.conf import settings

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)
    bonus_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    spins = models.IntegerField(default=0, help_text="Available spins from referrals")
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random
            import string
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not Customer.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.phone})"

import uuid

class Pet(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('UNKNOWN', 'Unknown'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50)  # Dog, Cat, etc.
    breed = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='UNKNOWN')
    color = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    microchip = models.CharField(max_length=50, blank=True)
    timeline_uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    
    @property
    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return 0
    
    def __str__(self):
        return f"{self.name} ({self.species})"

class MedicalRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('DIAGNOSIS', 'Diagnosis'),
        ('TREATMENT', 'Treatment'),
        ('SURGERY', 'Surgery'),
        ('VACCINATION', 'Vaccination'),
        ('OTHER', 'Other'),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='medical_records')
    veterinarian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_records_authored")
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES, default='DIAGNOSIS')
    description = models.TextField()
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    additional_conditions = models.TextField(blank=True, help_text="Qo'shimcha kasalliklar (ixtiyoriy)")
    # New JSON field for structured analysis results (dynamic indicators)
    analysis_data = models.JSONField(null=True, blank=True)
    # Link to Consumable Sets for Smart Write-off (using string reference to avoid circular import)
    consumable_sets = models.ManyToManyField('shop.ConsumableSet', blank=True, related_name='medical_records')
    date = models.DateTimeField(default=timezone.now)
    follow_up_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.pet.name} - {self.record_type} - {self.date.date()}"

class Visit(models.Model):
    STATUS_CHOICES = [
        ('WAITING', 'Waiting'),
        ('CALLED', 'Called'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    URGENCY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='visits')
    veterinarian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="visits_conducted")
    purpose = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='LOW')
    arrived_at = models.DateTimeField(auto_now_add=True)
    queue_number = models.CharField(max_length=10, null=True, blank=True) # Changed to CharField for A001 format
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus_credited = models.BooleanField(default=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_status = self.status

    def save(self, *args, **kwargs):
        if not self.queue_number:
            today = timezone.now().date()
            prefix = "N" # Default prefix if no doctor assigned
            
            if self.veterinarian:
                if self.veterinarian.queue_prefix:
                    prefix = self.veterinarian.queue_prefix
                elif self.veterinarian.first_name:
                    # Fallback to first letter of first name
                    prefix = self.veterinarian.first_name[0].upper()
            
            # Find the last queue number for THIS doctor (or default) today
            last_visit = Visit.objects.filter(
                arrived_at__date=today,
                queue_number__startswith=prefix
            ).order_by('-arrived_at').first()
            
            next_num = 1
            if last_visit and last_visit.queue_number:
                try:
                    # Extract numeric part from A001 -> 1
                    last_num_str = "".join(filter(str.isdigit, last_visit.queue_number))
                    if last_num_str:
                        next_num = int(last_num_str) + 1
                except ValueError:
                    pass
            
            self.queue_number = f"{prefix}{next_num:03d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Visit {self.queue_number}: {self.pet.name} - {self.status} ({self.urgency_level})"

class FollowUp(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='follow_up')
    scheduled_date = models.DateField()
    description = models.TextField(blank=True)
    notified_3d = models.BooleanField(default=False)
    notified_2d = models.BooleanField(default=False)
    notified_1d = models.BooleanField(default=False)
    notified_today = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False) # True if they show up
    no_show_notified_count = models.IntegerField(default=0) # Up to 3 days

    def __str__(self):
        return f"FollowUp for {self.visit.pet.name} on {self.scheduled_date}"

class VisitFeedback(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.visit.id}: {self.rating}/5"

class VaccineSchedule(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccines')
    vaccine_name = models.CharField(max_length=100)
    last_date = models.DateField()
    next_date = models.DateField()
    interval_days = models.IntegerField(default=365)
    notified = models.BooleanField(default=False)
    veterinarian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="vaccinations_administered")

    def __str__(self):
        return f"{self.pet.name} - {self.vaccine_name} ({self.next_date})"

class PrintJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('printed', 'Printed'),
        ('failed', 'Failed'),
    ]
    data = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job {self.id} - {self.status}"

class AnalysisTemplate(models.Model):
    """
    Template for specific analysis types (e.g., 'Umumiy Qon Tahlili', 'Siydik Tahlili').
    Stores the structure and normal ranges for indicators.
    """
    title = models.CharField(max_length=255)
    # JSON structure: 
    # [
    #   {"key": "wbc", "label": "Leykotsitlar (WBC)", "unit": "10^9/L", "min": 6.0, "max": 17.0},
    #   ...
    # ]
    indicators_schema = models.JSONField(default=list, help_text="List of indicators with ranges")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Prescription(models.Model):
    """
    Digital Prescription linked to a Medical Record.
    """
    medical_record = models.OneToOneField(MedicalRecord, on_delete=models.CASCADE, related_name='prescription')
    notes = models.TextField(blank=True, help_text="General notes for the owner")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.medical_record.pet.name} - {self.created_at.date()}"

class PrescriptionItem(models.Model):
    """
    Individual drug in a prescription with dosage instructions.
    """
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text="e.g. '1 tabletka' or '2 ml'")
    duration_days = models.IntegerField(default=1)
    
    # Pictogram flags for time of day
    morning = models.BooleanField(default=False)
    afternoon = models.BooleanField(default=False)
    evening = models.BooleanField(default=False)
    
    # E.g. "Before food", "After food"
    instruction = models.CharField(max_length=255, blank=True)

    def __str__(self):
        times = []
        if self.morning: times.append("☀️")
        if self.afternoon: times.append("🌤️")
        if self.evening: times.append("🌙")
        return f"{self.drug_name}: {self.dosage} ({' '.join(times)})"
