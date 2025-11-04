"""
XSS protection template tags for AHSP referensi app.

This module provides template filters for safely displaying user-generated
content and data from Excel imports, preventing XSS attacks.

Features:
- HTML tag stripping with bleach library
- Allowed tag whitelisting
- URL sanitization
- Attribute filtering
- Line break preservation
"""

from __future__ import annotations

from django import template
from django.utils.html import escape, linebreaks
from django.utils.safestring import mark_safe, SafeString

try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False

register = template.Library()


# Allowed HTML tags for rich content (when needed)
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'span', 'div', 'pre', 'code',
]

# Allowed attributes
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'rel'],
    'span': ['class', 'style'],
    'div': ['class', 'style'],
}

# Allowed protocols for links
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


@register.filter(name='safe_ahsp_display')
def safe_ahsp_display(value: any) -> SafeString:
    """
    Safely display AHSP data, removing all HTML tags.

    This is the primary filter for displaying user data from Excel imports.
    It strips ALL HTML tags and escapes special characters to prevent XSS.

    Usage:
        {{ job.nama_ahsp|safe_ahsp_display }}
        {{ detail.uraian_item|safe_ahsp_display }}

    Args:
        value: Input value (can be any type)

    Returns:
        Sanitized string safe for HTML display
    """
    if value is None:
        return ''

    # Convert to string
    text = str(value)

    if not text:
        return ''

    if BLEACH_AVAILABLE:
        # Use bleach to strip all tags and escape
        cleaned = bleach.clean(
            text,
            tags=[],  # No tags allowed
            strip=True,  # Strip tags completely
        )
        # Bleach already escapes special characters, but ensure it's escaped
        # by not using mark_safe for user content
        return cleaned
    else:
        # Fallback: use Django's escape
        return escape(text)


@register.filter(name='safe_rich_display')
def safe_rich_display(value: any) -> SafeString:
    """
    Display rich content with allowed HTML tags.

    Use this for content where some HTML formatting is needed,
    but still needs XSS protection.

    Usage:
        {{ description|safe_rich_display }}

    Args:
        value: Input value

    Returns:
        Sanitized HTML string
    """
    if value is None:
        return ''

    text = str(value)

    if not text:
        return ''

    if BLEACH_AVAILABLE:
        # Use bleach with allowed tags
        cleaned = bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
        )

        # Linkify URLs (make them clickable)
        cleaned = bleach.linkify(
            cleaned,
            parse_email=True,
        )
    else:
        # Fallback: escape and convert line breaks
        cleaned = linebreaks(escape(text))

    return mark_safe(cleaned)


@register.filter(name='safe_truncate')
def safe_truncate(value: any, length: int = 100) -> SafeString:
    """
    Safely truncate and display text.

    Usage:
        {{ long_text|safe_truncate:50 }}

    Args:
        value: Input value
        length: Maximum length (default: 100)

    Returns:
        Truncated, sanitized string
    """
    if value is None:
        return ''

    text = str(value)

    # Sanitize first
    safe_text = safe_ahsp_display(text)

    # Truncate
    if len(safe_text) > length:
        return mark_safe(safe_text[:length] + '...')

    return safe_text


@register.filter(name='safe_line_breaks')
def safe_line_breaks(value: any) -> SafeString:
    """
    Convert line breaks to <br> tags safely.

    Usage:
        {{ multiline_text|safe_line_breaks }}

    Args:
        value: Input value with line breaks

    Returns:
        Sanitized HTML with <br> tags
    """
    if value is None:
        return ''

    text = str(value)

    if not text:
        return ''

    # Sanitize first (remove all HTML)
    if BLEACH_AVAILABLE:
        cleaned = bleach.clean(text, tags=[], strip=True)
    else:
        cleaned = escape(text)

    # Replace newlines with <br>
    html = cleaned.replace('\n', '<br>')

    return mark_safe(html)


@register.filter(name='safe_code_display')
def safe_code_display(value: any) -> SafeString:
    """
    Display code or technical data safely.

    Preserves whitespace and uses monospace formatting.

    Usage:
        {{ code_snippet|safe_code_display }}

    Args:
        value: Input code/technical text

    Returns:
        Sanitized HTML in <pre><code> tags
    """
    if value is None:
        return ''

    text = str(value)

    if not text:
        return ''

    # Sanitize
    if BLEACH_AVAILABLE:
        cleaned = bleach.clean(text, tags=[], strip=True)
    else:
        cleaned = escape(text)

    # Wrap in pre/code tags
    html = f'<pre><code>{cleaned}</code></pre>'

    return mark_safe(html)


@register.filter(name='safe_search_highlight')
def safe_search_highlight(value: any, search_term: str = '') -> SafeString:
    """
    Highlight search terms in text safely.

    Usage:
        {{ text|safe_search_highlight:search_query }}

    Args:
        value: Input text
        search_term: Term to highlight

    Returns:
        Sanitized HTML with highlighted search terms
    """
    if value is None or not search_term:
        return safe_ahsp_display(value)

    text = str(value)
    search_term = str(search_term).strip()

    if not text or not search_term:
        return safe_ahsp_display(text)

    # Sanitize first
    if BLEACH_AVAILABLE:
        cleaned = bleach.clean(text, tags=[], strip=True)
    else:
        cleaned = escape(text)

    # Highlight search term (case-insensitive)
    import re
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)

    def highlight_match(match):
        return f'<mark class="bg-warning">{match.group(0)}</mark>'

    highlighted = pattern.sub(highlight_match, cleaned)

    return mark_safe(highlighted)


@register.filter(name='safe_url')
def safe_url(value: any) -> str:
    """
    Sanitize URL to prevent javascript: and data: URIs.

    Usage:
        <a href="{{ url|safe_url }}">Link</a>

    Args:
        value: Input URL

    Returns:
        Sanitized URL or empty string if dangerous
    """
    if value is None:
        return ''

    url = str(value).strip()

    if not url:
        return ''

    # Convert to lowercase for checking
    url_lower = url.lower()

    # Block dangerous protocols
    dangerous_protocols = [
        'javascript:',
        'data:',
        'vbscript:',
        'file:',
        'about:',
    ]

    for protocol in dangerous_protocols:
        if url_lower.startswith(protocol):
            return ''

    # Only allow safe protocols
    safe_protocols = ['http://', 'https://', 'mailto:', '/', '#']

    is_safe = any(url_lower.startswith(protocol) for protocol in safe_protocols)

    if not is_safe:
        return ''

    if BLEACH_AVAILABLE:
        # Additional sanitization with bleach
        cleaned = bleach.clean(url, tags=[], strip=True)
        return cleaned

    return escape(url)


@register.filter(name='safe_filename')
def safe_filename(value: any) -> SafeString:
    """
    Safely display filenames.

    Usage:
        {{ uploaded_file.name|safe_filename }}

    Args:
        value: Filename

    Returns:
        Sanitized filename
    """
    if value is None:
        return ''

    filename = str(value)

    if not filename:
        return ''

    # Remove path separators to prevent directory traversal display
    filename = filename.replace('/', '').replace('\\', '')

    # Sanitize
    if BLEACH_AVAILABLE:
        cleaned = bleach.clean(filename, tags=[], strip=True)
    else:
        cleaned = escape(filename)

    return mark_safe(cleaned)


# Utility functions for Python code

def sanitize_text(text: str, allow_html: bool = False) -> str:
    """
    Sanitize text in Python code (not a template filter).

    Usage:
        from referensi.templatetags.safe_display import sanitize_text

        clean_text = sanitize_text(user_input)

    Args:
        text: Input text
        allow_html: Whether to allow safe HTML tags

    Returns:
        Sanitized string
    """
    if not text:
        return ''

    text = str(text)

    if BLEACH_AVAILABLE:
        if allow_html:
            return bleach.clean(
                text,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                protocols=ALLOWED_PROTOCOLS,
                strip=True,
            )
        else:
            return bleach.clean(text, tags=[], strip=True)
    else:
        return escape(text)


def sanitize_url_python(url: str) -> str:
    """
    Sanitize URL in Python code (not a template filter).

    Args:
        url: Input URL

    Returns:
        Sanitized URL or empty string
    """
    if not url:
        return ''

    url = str(url).strip()
    url_lower = url.lower()

    # Block dangerous protocols
    dangerous_protocols = [
        'javascript:',
        'data:',
        'vbscript:',
        'file:',
        'about:',
    ]

    for protocol in dangerous_protocols:
        if url_lower.startswith(protocol):
            return ''

    if BLEACH_AVAILABLE:
        return bleach.clean(url, tags=[], strip=True)

    return escape(url)
