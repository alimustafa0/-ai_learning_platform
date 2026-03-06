from django import template
from datetime import date, timedelta
from ..models import LearningActivity

register = template.Library()

@register.inclusion_tag('courses/heatmap.html')
def render_heatmap(user, weeks=26):
    """
    Render a GitHub-style heatmap of learning activity.
    """
    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    # Get all activities in date range
    activities = LearningActivity.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')

    # Create a dictionary for easy lookup
    activity_dict = {act.date: act for act in activities}

    # Generate calendar grid
    calendar = []
    current_date = start_date

    while current_date <= end_date:
        week = []
        for i in range(7):
            if current_date <= end_date:
                activity = activity_dict.get(current_date)
                week.append({
                    'date': current_date,
                    'count': activity.count if activity else 0,
                    'xp': activity.xp_earned if activity else 0,
                    'has_activity': activity is not None,
                })
            else:
                week.append(None)
            current_date += timedelta(days=1)
        calendar.append(week)

    # Calculate max count for intensity scaling
    max_count = max([a.count for a in activities]) if activities else 1

    return {
        'calendar': calendar,
        'max_count': max_count,
        'weeks': weeks,
    }
