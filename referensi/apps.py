import os
import logging
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model
from django.test import Client

logger = logging.getLogger(__name__)


class ReferensiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'referensi'

    def ready(self):
        """
        Import signals when app is ready.

        PHASE 3: Register cache invalidation signals.
        """
        import referensi.signals  # noqa: F401
        post_migrate.connect(self._warmup_search_endpoint, dispatch_uid="referensi.warmup_search", weak=False)

    def _warmup_search_endpoint(self, **kwargs):
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            return
        User = get_user_model()
        client = Client()
        user, _ = User.objects.get_or_create(username="__search_warmup__", defaults={"email": "warmup@example.com"})
        client.force_login(user)
        try:
            client.get("/referensi/api/search", {"q": "warmup"})
        except Exception as exc:
            logger.debug("Search warmup skipped: %s", exc)
