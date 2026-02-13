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