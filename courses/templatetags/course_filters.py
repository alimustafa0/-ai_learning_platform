# courses/templatetags/course_filters.py
from django import template

register = template.Library()

@register.filter
def length_where(courses, condition):
    """
    Filter courses by condition and return count.
    Usage: {{ courses|length_where:"is_free=True" }}
    """
    if condition == "is_free=True":
        return sum(1 for course in courses if course.is_free())
    elif condition == "is_free=False":
        return sum(1 for course in courses if not course.is_free())
    return 0

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ distribution|get_item:rating }}
    """
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    """
    Multiply the value by the argument.
    Usage: {{ value|multiply:100 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    Calculate percentage.
    Usage: {{ value|percentage:total }}
    """
    try:
        if total and float(total) > 0:
            return (float(value) / float(total)) * 100
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def helpful_button_class(review, user):
    """Return the appropriate button class for helpful vote"""
    if review.user == user:
        return 'btn-outline-secondary" disabled'
    elif review.user_found_helpful(user):
        return 'btn-primary'
    else:
        return 'btn-outline-primary'
