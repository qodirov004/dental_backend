from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        from django.db.models.signals import post_save, post_delete
        from .signals import audit_log_save, audit_log_delete
        from django.apps import apps

        # Models to audit
        target_apps = ['clinic', 'shop', 'billing', 'users']
        
        for app_label in target_apps:
            try:
                app_config = apps.get_app_config(app_label)
                for model in app_config.get_models():
                    # Skip AuditLog itself to avoid recursion
                    if model._meta.model_name == 'auditlog':
                        continue
                        
                    post_save.connect(audit_log_save, sender=model)
                    post_delete.connect(audit_log_delete, sender=model)
            except LookupError:
                pass
