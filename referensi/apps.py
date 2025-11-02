from django.apps import AppConfig


class ReferensiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'referensi'

    def ready(self):
        """
        Import signals when app is ready.

        PHASE 3: Register cache invalidation signals.
        """
        import referensi.signals  # noqa: F401
