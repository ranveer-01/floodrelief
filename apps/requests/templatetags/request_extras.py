"""Small presentation helpers for the request templates."""
from django import template

from apps.requests.models import format_minutes

register = template.Library()


@register.filter(name="minutes")
def minutes(value):
    """Render a float number of minutes as '18 min' / '3 h 05 m'."""
    if value is None:
        return "—"
    try:
        return format_minutes(float(value))
    except (TypeError, ValueError):
        return "—"


@register.filter(name="iso")
def iso(value):
    """ISO-8601 stamp for the `datetime` attribute of <time> elements."""
    return value.isoformat() if value else ""
