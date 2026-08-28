from django import template

register = template.Library()


@register.filter
def initials(name):
    parts = [p for p in name.split() if p]
    letters = "".join(p[0] for p in parts[:2])
    return letters.upper()
