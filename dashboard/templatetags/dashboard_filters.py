"""
Custom template filters for dashboard app.
"""

from django import template
from datetime import date

register = template.Library()


@register.filter(name='timesince_days')
def timesince_days(start_date, end_date=None):
    """
    Calculate the number of days between start_date and end_date (or today).

    Usage in template:
        {{ project.tanggal_mulai|timesince_days }}  # Days from start to today
        {{ project.tanggal_mulai|timesince_days:project.tanggal_selesai }}  # Days between two dates

    Args:
        start_date: The starting date (datetime.date or datetime.datetime)
        end_date: The ending date (optional, defaults to today)

    Returns:
        int: Number of days between the dates
    """
    if start_date is None:
        return 0

    # Convert datetime to date if needed
    if hasattr(start_date, 'date'):
        start_date = start_date.date()

    # If no end_date provided, use today
    if end_date is None:
        end_date = date.today()
    elif hasattr(end_date, 'date'):
        end_date = end_date.date()

    # Calculate difference
    try:
        delta = (end_date - start_date).days
        return max(0, delta)  # Don't return negative days
    except (TypeError, AttributeError):
        return 0
