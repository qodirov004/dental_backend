from django.apps import AppConfig

class GamesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'games'
    verbose_name = "O'yin Sozlamalari (Lucky Tower)"

    def ready(self):
        import games.signals
