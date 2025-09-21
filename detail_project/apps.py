from django.apps import AppConfig


class DetailProjectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'detail_project'
    def ready(self):
        from . import signals  # noqa: F401
