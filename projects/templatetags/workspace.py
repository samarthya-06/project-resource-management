from django import template

register = template.Library()


@register.filter
def duration(minutes):
    hours, remainder = divmod(int(minutes or 0), 60)
    return f"{hours}h {remainder:02d}m" if remainder else f"{hours}h"
