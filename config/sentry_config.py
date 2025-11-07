"""
Sentry Configuration

Sentry error tracking integration for production monitoring.

Setup:
    1. Create Sentry account: https://sentry.io
    2. Create new project
    3. Get DSN from project settings
    4. Set SENTRY_DSN environment variable
    5. Import this in settings.py

Features:
    - Automatic error tracking
    - Performance monitoring
    - Release tracking
    - User context
    - Custom tags
    - Breadcrumbs
"""

import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging


def init_sentry():
    """
    Initialize Sentry SDK for error tracking.

    Environment Variables:
        SENTRY_DSN: Sentry project DSN
        SENTRY_ENVIRONMENT: Environment name (production, staging, development)
        SENTRY_TRACES_SAMPLE_RATE: Sample rate for performance monitoring (0.0-1.0)
        APP_VERSION: Application version for release tracking
    """
    sentry_dsn = os.environ.get('SENTRY_DSN')

    if not sentry_dsn:
        logging.info('Sentry DSN not configured, error tracking disabled')
        return

    environment = os.environ.get('SENTRY_ENVIRONMENT', 'development')
    traces_sample_rate = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
    release = os.environ.get('APP_VERSION', 'unknown')

    # Configure logging integration
    # Capture ERROR and above to Sentry
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Breadcrumbs level
        event_level=logging.ERROR  # Events sent to Sentry
    )

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=release,

        # Integrations
        integrations=[
            DjangoIntegration(),
            RedisIntegration(),
            logging_integration,
        ],

        # Performance Monitoring
        traces_sample_rate=traces_sample_rate,

        # Error Sampling
        # In production, you might want to sample errors to reduce costs
        # sample_rate=1.0,  # 100% of errors

        # Send default PII (Personally Identifiable Information)
        send_default_pii=True,

        # Before send hook (for filtering/modifying events)
        before_send=before_send_hook,

        # Before breadcrumb hook
        before_breadcrumb=before_breadcrumb_hook,

        # Attach stack trace to messages
        attach_stacktrace=True,

        # Max breadcrumbs
        max_breadcrumbs=50,

        # Debug mode (only enable in development)
        debug=environment == 'development',
    )

    logging.info(f'Sentry initialized: env={environment}, release={release}')


def before_send_hook(event, hint):
    """
    Hook called before sending event to Sentry.

    Use this to:
    - Filter out certain errors
    - Add custom tags
    - Scrub sensitive data
    - Modify event data

    Args:
        event: Event dictionary
        hint: Additional context

    Returns:
        Modified event or None to drop event
    """
    # Example: Don't send certain exceptions
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']

        # Don't send 404 errors to Sentry
        if exc_type.__name__ == 'Http404':
            return None

        # Don't send validation errors
        if exc_type.__name__ == 'ValidationError':
            return None

    # Example: Add custom tags
    event.setdefault('tags', {})
    event['tags']['app'] = 'ahsp'

    # Example: Scrub sensitive data from request
    if 'request' in event:
        if 'data' in event['request']:
            # Remove password fields
            if isinstance(event['request']['data'], dict):
                event['request']['data'].pop('password', None)
                event['request']['data'].pop('secret_key', None)

    return event


def before_breadcrumb_hook(crumb, hint):
    """
    Hook called before adding breadcrumb.

    Use this to:
    - Filter breadcrumbs
    - Modify breadcrumb data
    - Add context

    Args:
        crumb: Breadcrumb dictionary
        hint: Additional context

    Returns:
        Modified breadcrumb or None to drop
    """
    # Example: Don't track health check requests
    if crumb.get('category') == 'httplib':
        if '/health/' in crumb.get('data', {}).get('url', ''):
            return None

    return crumb


def capture_exception_with_context(exception, **context):
    """
    Capture exception with additional context.

    Args:
        exception: Exception instance
        **context: Additional context key-value pairs

    Example:
        try:
            risky_operation()
        except Exception as e:
            capture_exception_with_context(
                e,
                user_id=request.user.id,
                project_id=project.id,
                operation='deep_copy'
            )
    """
    with sentry_sdk.push_scope() as scope:
        # Add context
        for key, value in context.items():
            scope.set_context(key, {'value': value})

        # Capture exception
        sentry_sdk.capture_exception(exception)


def capture_message_with_level(message, level='info', **context):
    """
    Capture message with specific level.

    Args:
        message: Message string
        level: Log level (debug, info, warning, error, fatal)
        **context: Additional context

    Example:
        capture_message_with_level(
            'User performed bulk operation',
            level='info',
            user_id=user.id,
            operation_count=50
        )
    """
    with sentry_sdk.push_scope() as scope:
        # Add context
        for key, value in context.items():
            scope.set_context(key, {'value': value})

        # Capture message
        sentry_sdk.capture_message(message, level=level)


def set_user_context(user):
    """
    Set user context for Sentry events.

    Call this in middleware or views to associate errors with users.

    Args:
        user: Django User instance
    """
    if user and user.is_authenticated:
        sentry_sdk.set_user({
            'id': user.id,
            'username': user.username,
            'email': user.email,
        })
    else:
        sentry_sdk.set_user(None)


def add_breadcrumb(message, category='custom', level='info', data=None):
    """
    Add custom breadcrumb for context.

    Breadcrumbs are shown in Sentry issue details to understand
    what happened before an error.

    Args:
        message: Breadcrumb message
        category: Category (http, navigation, query, etc.)
        level: Level (debug, info, warning, error)
        data: Additional data dict

    Example:
        add_breadcrumb(
            'User started deep copy',
            category='user_action',
            data={'source_project_id': 123}
        )
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


class SentryContextMiddleware:
    """
    Middleware to add Sentry context to requests.

    Add to MIDDLEWARE in settings.py:
        'config.sentry_config.SentryContextMiddleware',
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set user context
        if hasattr(request, 'user'):
            set_user_context(request.user)

        # Add request info to scope
        with sentry_sdk.push_scope() as scope:
            scope.set_tag('request_method', request.method)
            scope.set_tag('request_path', request.path)

            # Add custom context
            scope.set_context('request_info', {
                'method': request.method,
                'path': request.path,
                'query_string': request.META.get('QUERY_STRING', ''),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            })

            response = self.get_response(request)

            # Add response status
            scope.set_tag('response_status', response.status_code)

        return response


# Example usage in views
"""
from config.sentry_config import capture_exception_with_context, add_breadcrumb

def my_view(request):
    add_breadcrumb('User accessed my_view', category='navigation')

    try:
        # Your code
        process_data()

    except Exception as e:
        capture_exception_with_context(
            e,
            view='my_view',
            user_id=request.user.id,
            additional_info='Something went wrong'
        )
        raise
"""


# Example settings.py integration
"""
# settings.py

from config.sentry_config import init_sentry

# Initialize Sentry (only in production/staging)
if not DEBUG:
    init_sentry()

# Or always initialize but with different sample rates
init_sentry()

# Add middleware
MIDDLEWARE = [
    # ... other middleware
    'config.sentry_config.SentryContextMiddleware',
    # ... other middleware
]
"""
