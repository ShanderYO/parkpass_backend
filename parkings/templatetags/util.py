from django import template

from rps_vendor.models import Developer

register = template.Library()

@register.filter
def isDeveloperPage(original):
    return isinstance(original, Developer)