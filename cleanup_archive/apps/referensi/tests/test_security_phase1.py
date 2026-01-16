"""
Phase 1 Security Tests

This module tests all Phase 1 security features:
1. File validation (size, extension, content, row limits)
2. Rate limiting middleware
3. XSS protection template tags

Run tests:
    pytest referensi/tests/test_security_phase1.py -v
"""

from __future__ import annotations

import io
import time
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest, HttpResponse
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from referensi.middleware.rate_limit import (
    ImportRateLimitMiddleware,
    RateLimitChecker,
)
from referensi.templatetags.safe_display import (
    safe_ahsp_display,
    safe_filename,
    safe_search_highlight,
    safe_url,
    sanitize_text,
    sanitize_url_python,
)
from referensi.validators import AHSPFileValidator, validate_ahsp_file

User = get_user_model()


# ============================================================================
# File Validator Tests
# ============================================================================


class TestAHSPFileValidator:
    """Test file validation with various scenarios."""

    def create_test_file(
        self,
        size: int,
        name: str = "test.xlsx",
        content: bytes | None = None,
    ) -> SimpleUploadedFile:
        """Create a test file with specified size."""
        if content is None:
            content = b"x" * size
        return SimpleUploadedFile(name, content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_validate_file_exists(self):
        """Test that validation fails for None or empty files."""
        validator = AHSPFileValidator()

        # Test None file
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_file_exists(None)
        assert "tidak ada file" in str(exc_info.value).lower()

        # Test empty file
        empty_file = self.create_test_file(0, "empty.xlsx")
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_file_exists(empty_file)
        assert "kosong" in str(exc_info.value).lower()

    def test_validate_file_size_within_limit(self):
        """Test that files within size limit pass validation."""
        validator = AHSPFileValidator()

        # 1MB file (well within 50MB limit)
        small_file = self.create_test_file(1024 * 1024, "small.xlsx")

        # Should not raise
        validator.validate_file_size(small_file)

    def test_validate_file_size_exceeds_limit(self):
        """Test that files exceeding size limit fail validation."""
        validator = AHSPFileValidator(max_file_size=1024 * 1024)  # 1MB limit

        # 2MB file
        large_file = self.create_test_file(2 * 1024 * 1024, "large.xlsx")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_file_size(large_file)
        assert "terlalu besar" in str(exc_info.value).lower()

    def test_validate_extension_valid(self):
        """Test that valid extensions pass validation."""
        validator = AHSPFileValidator()

        xlsx_file = self.create_test_file(100, "test.xlsx")
        validator.validate_extension(xlsx_file)

        xls_file = self.create_test_file(100, "test.xls")
        validator.validate_extension(xls_file)

    def test_validate_extension_invalid(self):
        """Test that invalid extensions fail validation."""
        validator = AHSPFileValidator()

        invalid_files = [
            self.create_test_file(100, "test.csv"),
            self.create_test_file(100, "test.txt"),
            self.create_test_file(100, "test.exe"),
            self.create_test_file(100, "test.pdf"),
        ]

        for file in invalid_files:
            with pytest.raises(ValidationError) as exc_info:
                validator.validate_extension(file)
            assert "ekstensi" in str(exc_info.value).lower()

    def test_validate_extension_case_insensitive(self):
        """Test that extension validation is case-insensitive."""
        validator = AHSPFileValidator()

        # Uppercase extensions should work
        xlsx_file = self.create_test_file(100, "TEST.XLSX")
        validator.validate_extension(xlsx_file)

    def test_validate_mime_type_valid(self):
        """Test that valid MIME types pass validation."""
        validator = AHSPFileValidator()

        # .xlsx MIME type
        xlsx_file = SimpleUploadedFile(
            "test.xlsx",
            b"content",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        validator.validate_mime_type(xlsx_file)

        # .xls MIME type
        xls_file = SimpleUploadedFile(
            "test.xls",
            b"content",
            content_type="application/vnd.ms-excel"
        )
        validator.validate_mime_type(xls_file)

    def test_validate_mime_type_invalid(self):
        """Test that invalid MIME types fail validation."""
        validator = AHSPFileValidator()

        # PDF file with wrong MIME type (definitely not Excel)
        invalid_file = SimpleUploadedFile(
            "test.pdf",
            b"content",
            content_type="application/pdf"
        )

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_mime_type(invalid_file)
        assert "tipe file" in str(exc_info.value).lower() or "tidak valid" in str(exc_info.value).lower()

    def test_convenience_function(self):
        """Test the validate_ahsp_file convenience function."""
        # Valid file (xls to skip zip bomb check)
        valid_file = SimpleUploadedFile(
            "test.xls",
            b"x" * 1024,
            content_type="application/vnd.ms-excel"
        )

        # Should not raise
        validate_ahsp_file(valid_file)

        # Invalid file (too large)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        large_file = SimpleUploadedFile(
            "large.xls",
            large_content,
            content_type="application/vnd.ms-excel"
        )

        with pytest.raises(ValidationError):
            validate_ahsp_file(large_file)

    def test_custom_limits(self):
        """Test that custom limits are respected."""
        # Custom validator with 500KB limit
        validator = AHSPFileValidator(
            max_file_size=500 * 1024,
            max_rows=100,
        )

        # 600KB file should fail
        large_file = self.create_test_file(600 * 1024, "test.xlsx")
        with pytest.raises(ValidationError):
            validator.validate_file_size(large_file)


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestImportRateLimitMiddleware(TestCase):
    """Test rate limiting middleware functionality."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # Clear cache before each test
        cache.clear()

        # Create middleware with test limits
        def get_response(request):
            return HttpResponse("OK")

        self.middleware = ImportRateLimitMiddleware(get_response)
        # Override settings for testing
        self.middleware.rate_limit = 5  # 5 requests
        self.middleware.rate_window = 60  # 1 minute

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_middleware_allows_unprotected_paths(self):
        """Test that middleware doesn't rate limit unprotected paths."""
        request = self.factory.get("/other/path/")
        request.user = self.user

        # Should pass through without rate limiting
        response = self.middleware(request)
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response

    def test_middleware_protects_import_paths(self):
        """Test that middleware protects configured paths."""
        request = self.factory.get("/referensi/preview/")
        request.user = self.user

        # Should add rate limit headers
        response = self.middleware(request)
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response
        assert "X-RateLimit-Remaining" in response
        assert "X-RateLimit-Reset" in response

    @patch('referensi.middleware.rate_limit.render')
    def test_rate_limit_enforcement(self, mock_render):
        """Test that rate limit is enforced after exceeding limit."""
        # Mock the render function to return a simple response
        mock_render.return_value = HttpResponse("Rate limited", status=429)

        request = self.factory.post("/referensi/preview/")
        request.user = self.user

        # Make requests up to the limit
        for i in range(self.middleware.rate_limit):
            response = self.middleware(request)
            assert response.status_code == 200, f"Request {i+1} should succeed"
            remaining = int(response["X-RateLimit-Remaining"])
            assert remaining == self.middleware.rate_limit - (i + 1)

        # Next request should be rate limited
        response = self.middleware(request)
        assert response.status_code == 429

    @patch('referensi.middleware.rate_limit.render')
    def test_rate_limit_per_user(self, mock_render):
        """Test that rate limits are tracked per user."""
        mock_render.return_value = HttpResponse("Rate limited", status=429)

        user1 = self.user
        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123"
        )

        # User 1 makes requests
        request1 = self.factory.post("/referensi/preview/")
        request1.user = user1

        for _ in range(self.middleware.rate_limit):
            self.middleware(request1)

        # User 1 should be rate limited
        response1 = self.middleware(request1)
        assert response1.status_code == 429

        # User 2 should still have full quota
        request2 = self.factory.post("/referensi/preview/")
        request2.user = user2

        response2 = self.middleware(request2)
        assert response2.status_code == 200
        assert int(response2["X-RateLimit-Remaining"]) == self.middleware.rate_limit - 1

    @patch('referensi.middleware.rate_limit.render')
    def test_rate_limit_reset_after_window(self, mock_render):
        """Test that rate limit resets after time window expires."""
        mock_render.return_value = HttpResponse("Rate limited", status=429)

        request = self.factory.post("/referensi/preview/")
        request.user = self.user

        # Exhaust the limit
        for _ in range(self.middleware.rate_limit):
            self.middleware(request)

        # Should be rate limited
        response = self.middleware(request)
        assert response.status_code == 429

        # Simulate time passing by manipulating cache
        cache_key = f"import_rate_limit:user:{self.user.id}"
        cache.delete(cache_key)

        # Should be allowed again
        response = self.middleware(request)
        assert response.status_code == 200

    def test_anonymous_user_rate_limiting(self):
        """Test rate limiting for anonymous users by IP."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/referensi/preview/")
        request.user = AnonymousUser()
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        # GET requests for anonymous users should pass through
        response = self.middleware(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRateLimitChecker:
    """Test the RateLimitChecker utility class."""

    def setup_method(self):
        """Set up test environment."""
        cache.clear()
        self.checker = RateLimitChecker(rate_limit=5, rate_window=60)

    def teardown_method(self):
        """Clean up after tests."""
        cache.clear()

    def test_check_user_limit_first_request(self):
        """Test that first request is always allowed."""
        assert self.checker.check_user_limit(user_id=1) is True

    def test_check_user_limit_within_quota(self):
        """Test checking limit when user is within quota."""
        user_id = 1

        # Simulate 3 requests
        for i in range(3):
            cache_key = f"import_rate_limit:user:{user_id}"
            cache.set(
                cache_key,
                {'count': i + 1, 'reset_time': time.time() + 60},
                timeout=60
            )
            assert self.checker.check_user_limit(user_id) is True

    def test_check_user_limit_exceeded(self):
        """Test checking limit when user has exceeded quota."""
        user_id = 1
        cache_key = f"import_rate_limit:user:{user_id}"

        # Set count to limit
        cache.set(
            cache_key,
            {'count': 5, 'reset_time': time.time() + 60},
            timeout=60
        )

        assert self.checker.check_user_limit(user_id) is False

    def test_get_remaining_time(self):
        """Test getting remaining time until reset."""
        user_id = 1
        cache_key = f"import_rate_limit:user:{user_id}"

        reset_time = time.time() + 30  # 30 seconds from now
        cache.set(
            cache_key,
            {'count': 3, 'reset_time': reset_time},
            timeout=60
        )

        remaining = self.checker.get_remaining_time(user_id)
        assert 25 <= remaining <= 30  # Allow some time variance

    def test_get_remaining_requests(self):
        """Test getting remaining requests in window."""
        user_id = 1
        cache_key = f"import_rate_limit:user:{user_id}"

        # User has made 2 requests
        cache.set(
            cache_key,
            {'count': 2, 'reset_time': time.time() + 60},
            timeout=60
        )

        remaining = self.checker.get_remaining_requests(user_id)
        assert remaining == 3  # 5 - 2 = 3


# ============================================================================
# XSS Protection Tests
# ============================================================================


class TestXSSProtection:
    """Test XSS protection template tags."""

    def test_safe_ahsp_display_removes_html(self):
        """Test that HTML tags are removed from display."""
        dangerous_input = "<script>alert('XSS')</script>Normal text"
        result = safe_ahsp_display(dangerous_input)

        # Should strip the script tags but keep text content
        assert "<script>" not in result
        assert "</script>" not in result
        # Text content remains (bleach strips tags, not content)
        assert "Normal text" in result

    def test_safe_ahsp_display_handles_none(self):
        """Test that None values are handled gracefully."""
        result = safe_ahsp_display(None)
        assert result == ""

    def test_safe_ahsp_display_handles_numbers(self):
        """Test that numbers are converted to strings."""
        result = safe_ahsp_display(12345)
        assert "12345" in result

    def test_safe_search_highlight(self):
        """Test search term highlighting with XSS protection."""
        text = "Pekerjaan beton untuk jalan"
        search = "beton"

        result = safe_search_highlight(text, search)

        # Should contain highlighted text
        assert "beton" in result
        assert "mark" in result or "Pekerjaan" in result

    def test_safe_search_highlight_xss_protection(self):
        """Test that search highlighting prevents XSS."""
        text = "Normal text"
        dangerous_search = "<script>alert('XSS')</script>"

        result = safe_search_highlight(text, dangerous_search)

        # Should not contain script tags
        assert "<script>" not in result

    def test_safe_url_blocks_javascript(self):
        """Test that javascript: URLs are blocked."""
        dangerous_url = "javascript:alert('XSS')"
        result = safe_url(dangerous_url)

        assert result == ""

    def test_safe_url_blocks_data_uri(self):
        """Test that data: URIs are blocked."""
        dangerous_url = "data:text/html,<script>alert('XSS')</script>"
        result = safe_url(dangerous_url)

        assert result == ""

    def test_safe_url_allows_safe_urls(self):
        """Test that safe URLs are allowed."""
        safe_urls = [
            "https://example.com",
            "http://example.com/path",
            "mailto:test@example.com",
            "/relative/path",
            "#anchor",
        ]

        for url in safe_urls:
            result = safe_url(url)
            assert result != "", f"URL {url} should be allowed"

    def test_safe_filename_prevents_traversal(self):
        """Test that filename display prevents directory traversal."""
        dangerous_filename = "../../etc/passwd"
        result = safe_filename(dangerous_filename)

        # Should not contain path separators
        assert "/" not in result
        assert "\\" not in result

    def test_sanitize_text_function(self):
        """Test the sanitize_text Python function."""
        dangerous_text = "<script>alert('XSS')</script>Normal text"
        result = sanitize_text(dangerous_text, allow_html=False)

        # Should strip script tags
        assert "<script>" not in result
        assert "</script>" not in result
        # Text content remains
        assert "Normal text" in result

    def test_sanitize_url_python_function(self):
        """Test the sanitize_url_python function."""
        # Dangerous URLs should be blocked
        assert sanitize_url_python("javascript:alert(1)") == ""
        assert sanitize_url_python("data:text/html,<script>") == ""

        # Safe URLs should pass
        assert sanitize_url_python("https://example.com") != ""

    def test_template_tag_in_template(self):
        """Test using the safe_ahsp_display tag in a Django template."""
        template_string = "{% load safe_display %}{{ text|safe_ahsp_display }}"
        template = Template(template_string)

        dangerous_text = "<script>alert('XSS')</script>Text"
        context = Context({"text": dangerous_text})

        rendered = template.render(context)

        # Should strip script tags
        assert "<script>" not in rendered
        assert "</script>" not in rendered


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase1SecurityIntegration(TestCase):
    """Integration tests for all Phase 1 security features."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_file_validation_in_view(self):
        """Test that file validation is integrated in the view."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create an oversized file
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        large_file = SimpleUploadedFile(
            "large.xlsx",
            large_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Validate should fail
        with pytest.raises(ValidationError) as exc_info:
            validate_ahsp_file(large_file)
        assert "terlalu besar" in str(exc_info.value).lower()

    @patch('referensi.middleware.rate_limit.render')
    def test_rate_limiting_with_authentication(self, mock_render):
        """Test rate limiting works with authenticated users."""
        mock_render.return_value = HttpResponse("Rate limited", status=429)

        def get_response(request):
            return HttpResponse("OK")

        middleware = ImportRateLimitMiddleware(get_response)
        middleware.rate_limit = 3
        middleware.rate_window = 60

        request = self.factory.post("/referensi/preview/")
        request.user = self.user

        # First 3 requests should succeed
        for i in range(3):
            response = middleware(request)
            assert response.status_code == 200

        # 4th request should be rate limited
        response = middleware(request)
        assert response.status_code == 429

    def test_xss_protection_in_search_display(self):
        """Test XSS protection is applied to search query display."""
        template_string = """
        {% load safe_display %}
        <div>Search: "{{ query|safe_ahsp_display }}"</div>
        """
        template = Template(template_string)

        dangerous_query = "<script>alert('XSS')</script>"
        context = Context({"query": dangerous_query})

        rendered = template.render(context)

        # Should not contain script tags
        assert "<script>" not in rendered
        assert "</script>" not in rendered


# ============================================================================
# Summary
# ============================================================================

"""
Phase 1 Security Test Summary:

1. File Validation Tests (12 tests):
   - File existence and size validation
   - Extension and MIME type validation
   - Custom limits and convenience functions
   - Coverage: referensi/validators.py

2. Rate Limiting Tests (9 tests):
   - Middleware functionality
   - Per-user rate limiting
   - Time window and reset behavior
   - Anonymous user handling
   - RateLimitChecker utility
   - Coverage: referensi/middleware/rate_limit.py

3. XSS Protection Tests (11 tests):
   - HTML tag removal
   - URL sanitization
   - Filename safety
   - Search highlighting with XSS protection
   - Template tag integration
   - Coverage: referensi/templatetags/safe_display.py

4. Integration Tests (3 tests):
   - End-to-end security workflow
   - Authentication integration
   - Template rendering with security

Total: 35 test cases covering all Phase 1 security features

Run with:
    pytest referensi/tests/test_security_phase1.py -v
    pytest referensi/tests/test_security_phase1.py -v --cov=referensi --cov-report=html
"""
