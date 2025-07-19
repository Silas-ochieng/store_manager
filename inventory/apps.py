from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = "Inventory Management"

    def ready(self):
        """
        Override this method to perform initialization tasks including signal registration.
        """
        # Import signals only after the app is fully loaded
        try:
            from . import signals  # noqa
            from django.db.models.signals import post_migrate
            from .setup import create_initial_data
            
            # Connect post-migrate signal for initial data setup
            post_migrate.connect(create_initial_data, sender=self)
            
            # Import checks for custom validation
            from . import checks  # noqa
        except ImportError:
            # Silently fail if signals.py doesn't exist yet
            pass