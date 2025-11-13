import logging
from django.apps import AppConfig
from django.db import connections
from django.db.backends.signals import connection_created
from django.db.models.signals import post_migrate


logger = logging.getLogger(__name__)
_SQLITE_EXPLAIN_PATCHED = False


def _patch_sqlite_explain():
    """Rewrite plain EXPLAIN to EXPLAIN QUERY PLAN for sqlite cursors."""
    global _SQLITE_EXPLAIN_PATCHED
    if _SQLITE_EXPLAIN_PATCHED:
        return
    from django.db.backends.utils import CursorWrapper

    original_execute = CursorWrapper.execute

    def execute(self, sql, params=None):
        if self.db.vendor == "sqlite" and isinstance(sql, str):
            stripped = sql.lstrip()
            upper = stripped.upper()
            if upper.startswith("EXPLAIN") and not upper.startswith("EXPLAIN QUERY PLAN"):
                remainder = stripped[len("EXPLAIN"):].lstrip()
                sql = f"EXPLAIN QUERY PLAN {remainder}"
        return original_execute(self, sql, params)

    CursorWrapper.execute = execute
    _SQLITE_EXPLAIN_PATCHED = True


def ensure_projectparameter_index(connection=None, using=None, **kwargs):
    """
    Ensure composite index on (project_id, name) exists for ProjectParameter when
    running in environments without migrations (e.g., sqlite in tests).
    """
    if connection is None:
        alias = using or "default"
        connection = connections[alias]

    if connection.vendor != "sqlite":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='detail_project_projectparameter'"
            )
            if not cursor.fetchone():
                return
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS detail_project_param_project_name_idx "
                "ON detail_project_projectparameter (project_id, name)"
            )
    except Exception as exc:
        logger.debug("ProjectParameter index creation skipped: %s", exc)


class DetailProjectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'detail_project'
    def ready(self):
        from . import signals  # noqa: F401
        _patch_sqlite_explain()
        connection_created.connect(
            ensure_projectparameter_index,
            dispatch_uid="detail_project.ensure_projectparameter_index",
            weak=False,
        )
        post_migrate.connect(
            ensure_projectparameter_index,
            dispatch_uid="detail_project.ensure_projectparameter_index.post_migrate",
            weak=False,
        )
