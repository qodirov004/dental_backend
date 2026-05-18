from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone

class SystemSettings(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value}"

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DOCTOR = "DOCTOR", "Shifokor (Stomatolog)"
        RECEPTIONIST = "RECEPTIONIST", "Registrator"
        ASSISTANT = "ASSISTANT", "Yordamchi"

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.ADMIN)
    salary_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Shifokorning har bir tashrifdan oladigan ulushi (%)")
    room_number = models.CharField(max_length=10, blank=True, null=True, help_text="Shifokor xonasi/kabinet raqami")
    queue_prefix = models.CharField(max_length=2, blank=True, null=True, help_text="Navbat raqami uchun harf (masalan: A, K, S)")

    def __str__(self):
        return f"{self.username} ({self.role})"

class DoctorSalary(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salary_withdrawals')
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_salaries')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor.username} - {self.amount} ({self.date.date()})"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.model_name} by {self.user} at {self.timestamp}"
