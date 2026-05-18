from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from users.models import AuditLog
from utils.middleware import get_current_user, get_current_ip
import json
from django.core.serializers.json import DjangoJSONEncoder

# List of models to track
# We will register them dynamically in apps.py or explicitly here if needed.
# For now, let's make a generic receiver and connect it manually.

def audit_log_save(sender, instance, created, **kwargs):
    if sender._meta.model_name == 'auditlog':
        return

    user = get_current_user()
    ip = get_current_ip()
    
    # If no user (e.g. system task or shell), we can skip or log as 'System'
    # But usually we only care about user actions.
    if not user or not user.is_authenticated:
        return

    action = 'CREATE' if created else 'UPDATE'
    changes = None

    if action == 'UPDATE':
        # This is a simple implementation. For full diffs, we'd need pre_save signal to compare.
        # For now, let's just log that an update happened.
        # To get real diffs, we need to fetch the old instance.
        pass

    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=sender._meta.model_name,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            changes=changes, # We can implement diff logic later if needed
            ip_address=ip
        )
    except Exception as e:
        print(f"Error creating audit log: {e}")

def audit_log_delete(sender, instance, **kwargs):
    if sender._meta.model_name == 'auditlog':
        return

    user = get_current_user()
    ip = get_current_ip()

    if not user or not user.is_authenticated:
        return

    try:
        AuditLog.objects.create(
            user=user,
            action='DELETE',
            model_name=sender._meta.model_name,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            ip_address=ip
        )
    except Exception as e:
        print(f"Error creating audit log: {e}")
