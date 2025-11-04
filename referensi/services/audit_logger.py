"""
Audit Logger Service - Phase 2

This service provides a centralized interface for logging security events
across the application. It integrates with the SecurityAuditLog model and
provides helper methods for common audit scenarios.

Features:
- Centralized logging interface
- Automatic user/IP extraction
- Integration with Django requests
- Async logging support
- Batch logging for performance
"""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.http import HttpRequest

from referensi.models import SecurityAuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Centralized audit logging service.

    Usage:
        from referensi.services.audit_logger import audit_logger

        # Log file validation
        audit_logger.log_file_validation(
            request=request,
            filename='test.xlsx',
            success=True,
            file_size=1024
        )

        # Log rate limit
        audit_logger.log_rate_limit_exceeded(
            request=request,
            limit=10,
            window=3600
        )
    """

    @staticmethod
    def _extract_request_info(request: HttpRequest | None) -> dict[str, Any]:
        """
        Extract user, IP, and request metadata from Django request.

        Args:
            request: Django HttpRequest or None

        Returns:
            Dictionary with user, ip_address, user_agent, path, method
        """
        if request is None:
            return {
                'user': None,
                'ip_address': None,
                'user_agent': '',
                'path': '',
                'method': '',
            }

        # Get user
        user = request.user if request.user.is_authenticated else None

        # Get IP address (handle proxy headers)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get path and method
        path = request.path
        method = request.method

        return {
            'user': user,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'path': path,
            'method': method,
        }

    # =========================================================================
    # File Upload Logging
    # =========================================================================

    def log_file_validation(
        self,
        request: HttpRequest | None,
        filename: str,
        success: bool,
        file_size: int | None = None,
        reason: str | None = None,
        **metadata
    ) -> SecurityAuditLog | None:
        """
        Log file validation attempt.

        Args:
            request: Django HttpRequest
            filename: Name of the uploaded file
            success: Whether validation succeeded
            file_size: File size in bytes
            reason: Failure reason (if success=False)
            **metadata: Additional metadata

        Returns:
            Created SecurityAuditLog instance or None if error
        """
        try:
            request_info = self._extract_request_info(request)

            if success:
                return SecurityAuditLog.log_file_validation_success(
                    user=request_info['user'],
                    ip_address=request_info['ip_address'],
                    filename=filename,
                    file_size=file_size or 0,
                    user_agent=request_info['user_agent'],
                    path=request_info['path'],
                    method=request_info['method'],
                    **metadata
                )
            else:
                return SecurityAuditLog.log_file_validation_failure(
                    user=request_info['user'],
                    ip_address=request_info['ip_address'],
                    filename=filename,
                    reason=reason or 'Unknown error',
                    user_agent=request_info['user_agent'],
                    path=request_info['path'],
                    method=request_info['method'],
                    **metadata
                )
        except Exception as e:
            logger.error(f"Failed to log file validation: {e}")
            return None

    def log_malicious_file_detected(
        self,
        request: HttpRequest | None,
        filename: str,
        threat_type: str,
        **metadata
    ) -> SecurityAuditLog | None:
        """
        Log detection of malicious file.

        Args:
            request: Django HttpRequest
            filename: Name of the malicious file
            threat_type: Type of threat (e.g., 'zip_bomb', 'dangerous_formula')
            **metadata: Additional metadata

        Returns:
            Created SecurityAuditLog instance or None if error
        """
        try:
            request_info = self._extract_request_info(request)

            log = SecurityAuditLog.log_malicious_file(
                user=request_info['user'],
                ip_address=request_info['ip_address'],
                filename=filename,
                threat_type=threat_type,
                user_agent=request_info['user_agent'],
                path=request_info['path'],
                method=request_info['method'],
                **metadata
            )

            # Also log to standard logger for immediate alerts
            logger.critical(
                f"SECURITY ALERT: Malicious file detected - {filename} ({threat_type}) "
                f"from IP {request_info['ip_address']}"
            )

            return log
        except Exception as e:
            logger.error(f"Failed to log malicious file: {e}")
            return None

    # =========================================================================
    # Rate Limiting Logging
    # =========================================================================

    def log_rate_limit_exceeded(
        self,
        request: HttpRequest | None,
        limit: int,
        window: int,
        **metadata
    ) -> SecurityAuditLog | None:
        """
        Log rate limit exceeded event.

        Args:
            request: Django HttpRequest
            limit: Rate limit (requests per window)
            window: Time window in seconds
            **metadata: Additional metadata

        Returns:
            Created SecurityAuditLog instance or None if error
        """
        try:
            request_info = self._extract_request_info(request)

            return SecurityAuditLog.log_rate_limit_exceeded(
                user=request_info['user'],
                ip_address=request_info['ip_address'],
                path=request_info['path'],
                limit=limit,
                window=window,
                user_agent=request_info['user_agent'],
                method=request_info['method'],
                **metadata
            )
        except Exception as e:
            logger.error(f"Failed to log rate limit: {e}")
            return None

    # =========================================================================
    # XSS Protection Logging
    # =========================================================================

    def log_xss_attempt(
        self,
        request: HttpRequest | None,
        input_field: str,
        dangerous_content: str,
        **metadata
    ) -> SecurityAuditLog | None:
        """
        Log XSS attempt.

        Args:
            request: Django HttpRequest
            input_field: Field name where XSS was detected
            dangerous_content: The dangerous content (truncated)
            **metadata: Additional metadata

        Returns:
            Created SecurityAuditLog instance or None if error
        """
        try:
            request_info = self._extract_request_info(request)

            log = SecurityAuditLog.log_xss_attempt(
                user=request_info['user'],
                ip_address=request_info['ip_address'],
                path=request_info['path'],
                input_field=input_field,
                dangerous_content=dangerous_content,
                user_agent=request_info['user_agent'],
                method=request_info['method'],
                **metadata
            )

            # Log warning for XSS attempts
            logger.warning(
                f"XSS attempt blocked: field={input_field}, "
                f"IP={request_info['ip_address']}, "
                f"content={dangerous_content[:50]}..."
            )

            return log
        except Exception as e:
            logger.error(f"Failed to log XSS attempt: {e}")
            return None

    # =========================================================================
    # Import Operation Logging
    # =========================================================================

    def log_import_operation(
        self,
        request: HttpRequest | None,
        filename: str,
        jobs_count: int,
        details_count: int,
        **metadata
    ) -> SecurityAuditLog | None:
        """
        Log successful import operation.

        Args:
            request: Django HttpRequest
            filename: Imported file name
            jobs_count: Number of jobs imported
            details_count: Number of details imported
            **metadata: Additional metadata

        Returns:
            Created SecurityAuditLog instance or None if error
        """
        try:
            request_info = self._extract_request_info(request)

            return SecurityAuditLog.log_import_operation(
                user=request_info['user'],
                ip_address=request_info['ip_address'],
                filename=filename,
                jobs_count=jobs_count,
                details_count=details_count,
                user_agent=request_info['user_agent'],
                path=request_info['path'],
                method=request_info['method'],
                **metadata
            )
        except Exception as e:
            logger.error(f"Failed to log import operation: {e}")
            return None

    # =========================================================================
    # Generic Logging Methods
    # =========================================================================

    def log_event(
        self,
        severity: str,
        category: str,
        event_type: str,
        message: str,
        request: HttpRequest | None = None,
        user: User | None = None,
        ip_address: str | None = None,
        **metadata
    ) -> SecurityAuditLog | None:
        """
        Generic method to log any security event.

        Args:
            severity: Severity level (info, warning, error, critical)
            category: Event category
            event_type: Specific event type
            message: Human-readable message
            request: Django HttpRequest (optional)
            user: User instance (optional, extracted from request if not provided)
            ip_address: IP address (optional, extracted from request if not provided)
            **metadata: Additional metadata

        Returns:
            Created SecurityAuditLog instance or None if error
        """
        try:
            # Extract from request if provided
            if request:
                request_info = self._extract_request_info(request)
                user = user or request_info['user']
                ip_address = ip_address or request_info['ip_address']
                metadata.update({
                    'user_agent': request_info['user_agent'],
                    'path': request_info['path'],
                    'method': request_info['method'],
                })

            return SecurityAuditLog.objects.create(
                severity=severity,
                category=category,
                event_type=event_type,
                message=message,
                user=user,
                ip_address=ip_address,
                metadata=metadata,
                path=metadata.get('path', ''),
                method=metadata.get('method', ''),
                user_agent=metadata.get('user_agent', ''),
            )
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return None

    # =========================================================================
    # Batch Logging
    # =========================================================================

    def log_batch(self, events: list[dict[str, Any]]) -> int:
        """
        Log multiple events in batch for performance.

        Args:
            events: List of event dictionaries with keys:
                - severity, category, event_type, message
                - Optional: user, ip_address, metadata, path, method

        Returns:
            Number of events successfully logged
        """
        logged_count = 0
        for event in events:
            try:
                SecurityAuditLog.objects.create(**event)
                logged_count += 1
            except Exception as e:
                logger.error(f"Failed to log batch event: {e}")

        return logged_count


# Singleton instance
audit_logger = AuditLogger()


# Convenience functions for direct use
def log_file_validation(request, filename, success, **kwargs):
    """Convenience function for file validation logging."""
    return audit_logger.log_file_validation(request, filename, success, **kwargs)


def log_malicious_file(request, filename, threat_type, **kwargs):
    """Convenience function for malicious file logging."""
    return audit_logger.log_malicious_file_detected(request, filename, threat_type, **kwargs)


def log_rate_limit(request, limit, window, **kwargs):
    """Convenience function for rate limit logging."""
    return audit_logger.log_rate_limit_exceeded(request, limit, window, **kwargs)


def log_xss_attempt(request, input_field, dangerous_content, **kwargs):
    """Convenience function for XSS attempt logging."""
    return audit_logger.log_xss_attempt(request, input_field, dangerous_content, **kwargs)


def log_import(request, filename, jobs_count, details_count, **kwargs):
    """Convenience function for import operation logging."""
    return audit_logger.log_import_operation(request, filename, jobs_count, details_count, **kwargs)
