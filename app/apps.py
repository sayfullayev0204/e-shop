from django.apps import AppConfig


class InventoryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Import the signals module to register the signal handlers
        import app.signals
