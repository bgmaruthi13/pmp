from django import template

register = template.Library()

_STATUS_PILLS = {
    "todo": "info",
    "in_progress": "warning",
    "done": "success",
}

_SENSITIVITY_PILLS = {
    "2-critical": "danger",
    "3-high": "warning",
    "4-medium": "info",
}


@register.filter
def status_pill(status):
    return _STATUS_PILLS.get(status, "")


@register.filter
def sensitivity_pill(sensitivity):
    return _SENSITIVITY_PILLS.get(sensitivity, "")
