from django.utils.cache import patch_cache_control


class DetailProjectNoStoreMiddleware:
    """
    Add no-store cache headers to dynamic detail_project HTML pages only.

    API endpoints, downloads, and non-HTML responses are intentionally skipped
    so file/export behavior is not changed by this page-cache hardening.
    """

    DETAIL_PROJECT_PREFIX = "/detail_project/"
    DETAIL_PROJECT_API_PREFIX = "/detail_project/api/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if self._should_apply(request, response):
            patch_cache_control(
                response,
                private=True,
                no_cache=True,
                no_store=True,
                must_revalidate=True,
            )
        return response

    def _should_apply(self, request, response):
        path = getattr(request, "path_info", None) or getattr(request, "path", "")
        if not path.startswith(self.DETAIL_PROJECT_PREFIX):
            return False
        if path.startswith(self.DETAIL_PROJECT_API_PREFIX):
            return False

        content_type = str(response.get("Content-Type", "")).lower()
        if "text/html" not in content_type:
            return False

        content_disposition = str(response.get("Content-Disposition", "")).lower()
        if content_disposition.startswith("attachment"):
            return False

        return True
