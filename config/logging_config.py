"""
Logging Configuration

Structured logging setup for Django application.
Provides JSON logging for production and human-readable logs for development.

Features:
- Structured JSON logging
- Log rotation
- Different levels per environment
- Request ID tracking
- User context
- Performance logging
"""

import os
import logging
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format.

    Useful for log aggregation systems (ELK, CloudWatch, Datadog).
    """

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        if hasattr(record, 'user'):
            log_data['user'] = record.user

        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint

        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration

        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'lineno', 'module', 'msecs', 'message',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                if not key.startswith('_'):
                    log_data[key] = value

        return json.dumps(log_data)


def get_logging_config(environment='development'):
    """
    Get logging configuration based on environment.

    Args:
        environment: 'development', 'staging', or 'production'

    Returns:
        dict: Django LOGGING configuration
    """

    # Base log level
    if environment == 'production':
        log_level = 'WARNING'
        console_formatter = 'json'
    elif environment == 'staging':
        log_level = 'INFO'
        console_formatter = 'json'
    else:
        log_level = 'DEBUG'
        console_formatter = 'verbose'

    return {
        'version': 1,
        'disable_existing_loggers': False,

        'formatters': {
            'verbose': {
                'format': '[{levelname}] {asctime} {name} {module}.{funcName}:{lineno} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'simple': {
                'format': '[{levelname}] {message}',
                'style': '{',
            },
            'json': {
                '()': 'config.logging_config.JSONFormatter',
            },
        },

        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },

        'handlers': {
            # Console handler (stdout)
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': console_formatter,
            },

            # File handler for all logs
            'file_all': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/application.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'formatter': 'json' if environment != 'development' else 'verbose',
            },

            # File handler for errors only
            'file_errors': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/errors.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
                'formatter': 'json' if environment != 'development' else 'verbose',
            },

            # File handler for performance logs
            'file_performance': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/performance.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
            },

            # File handler for security events
            'file_security': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/security.log',
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
                'formatter': 'json',
            },

            # Email handler for critical errors (production only)
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
                'filters': ['require_debug_false'],
                'formatter': 'verbose',
            },
        },

        'loggers': {
            # Django core
            'django': {
                'handlers': ['console', 'file_all'],
                'level': log_level,
                'propagate': False,
            },

            # Django requests
            'django.request': {
                'handlers': ['console', 'file_errors', 'mail_admins'],
                'level': 'ERROR',
                'propagate': False,
            },

            # Django database
            'django.db.backends': {
                'handlers': ['console'] if environment == 'development' else [],
                'level': 'DEBUG' if environment == 'development' else 'INFO',
                'propagate': False,
            },

            # Django security
            'django.security': {
                'handlers': ['console', 'file_security'],
                'level': 'WARNING',
                'propagate': False,
            },

            # Application loggers
            'detail_project': {
                'handlers': ['console', 'file_all', 'file_errors'],
                'level': log_level,
                'propagate': False,
            },

            'dashboard': {
                'handlers': ['console', 'file_all', 'file_errors'],
                'level': log_level,
                'propagate': False,
            },

            'referensi': {
                'handlers': ['console', 'file_all', 'file_errors'],
                'level': log_level,
                'propagate': False,
            },

            # Performance logger
            'performance': {
                'handlers': ['file_performance'],
                'level': 'INFO',
                'propagate': False,
            },

            # Security logger
            'security': {
                'handlers': ['file_security', 'console'],
                'level': 'WARNING',
                'propagate': False,
            },

            # Root logger (catch-all)
            '': {
                'handlers': ['console', 'file_all'],
                'level': log_level,
            },
        },
    }


class RequestIDMiddleware:
    """
    Middleware to add request ID to logs.

    Useful for tracing requests across logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import uuid

        # Generate request ID
        request_id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        request.request_id = request_id

        # Add to logger context (requires threading.local or contextvars)
        # For now, just add to request

        response = self.get_response(request)

        # Add request ID to response headers
        response['X-Request-ID'] = request_id

        return response


def log_performance(operation, duration, **context):
    """
    Log performance metrics.

    Args:
        operation: Operation name
        duration: Duration in seconds
        **context: Additional context
    """
    logger = logging.getLogger('performance')
    logger.info(
        f'Performance: {operation}',
        extra={
            'operation': operation,
            'duration': duration,
            **context
        }
    )


def log_security_event(event_type, severity='WARNING', **context):
    """
    Log security events.

    Args:
        event_type: Type of security event
        severity: Log level (WARNING, ERROR, CRITICAL)
        **context: Additional context
    """
    logger = logging.getLogger('security')
    log_method = getattr(logger, severity.lower())
    log_method(
        f'Security event: {event_type}',
        extra={
            'event_type': event_type,
            **context
        }
    )


# Usage examples
"""
# In views.py
import logging
from config.logging_config import log_performance, log_security_event
import time

logger = logging.getLogger(__name__)

def my_view(request):
    start_time = time.time()

    try:
        # Your code
        result = expensive_operation()

        # Log performance
        duration = time.time() - start_time
        log_performance('expensive_operation', duration, user_id=request.user.id)

        logger.info('Operation completed successfully', extra={
            'user': request.user.username,
            'operation': 'expensive_operation'
        })

    except Exception as e:
        logger.error('Operation failed', exc_info=True, extra={
            'user': request.user.username,
            'operation': 'expensive_operation'
        })
        raise

# In authentication code
def handle_failed_login(username, ip_address):
    log_security_event(
        'failed_login_attempt',
        severity='WARNING',
        username=username,
        ip_address=ip_address
    )

# In rate limiting code
def handle_rate_limit_exceeded(user, endpoint):
    log_security_event(
        'rate_limit_exceeded',
        severity='WARNING',
        user_id=user.id,
        username=user.username,
        endpoint=endpoint
    )
"""


# settings.py integration
"""
# settings.py
from config.logging_config import get_logging_config
import os

ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

# Logging configuration
LOGGING = get_logging_config(ENVIRONMENT)

# Add request ID middleware
MIDDLEWARE = [
    # ... other middleware
    'config.logging_config.RequestIDMiddleware',
    # ... other middleware
]

# Create logs directory if it doesn't exist
import os
os.makedirs('logs', exist_ok=True)
"""
