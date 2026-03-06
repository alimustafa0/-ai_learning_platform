# courses/templatetags/course_extras.py
from django import template
import re
import logging
import requests

from ..recommendations import get_course_recommendations, get_next_course_recommendation

register = template.Library()

# ===== EXISTING VIDEO EMBED FILTERS =====
@register.filter
def video_embed_url(url):
    """
    Convert YouTube and Vimeo URLs to embed format.
    """
    if not url:
        return url

    print(f"Original URL: {url}")  # Debug print

    # YouTube patterns - FIXED PATTERNS
    youtube_watch = r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
    match = re.search(youtube_watch, url)
    if match:
        video_id = match.group(1)
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        print(f"YouTube watch -> Embed: {embed_url}")
        return embed_url

    youtube_short = r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)'
    match = re.search(youtube_short, url)
    if match:
        video_id = match.group(1)
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        print(f"YouTube short -> Embed: {embed_url}")
        return embed_url

    youtube_embed = r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)'
    match = re.search(youtube_embed, url)
    if match:
        video_id = match.group(1)
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        print(f"YouTube embed -> Keeping: {embed_url}")
        return embed_url

    # Vimeo pattern
    vimeo_pattern = r'(?:https?://)?(?:www\.)?vimeo\.com/(\d+)'
    match = re.search(vimeo_pattern, url)
    if match:
        video_id = match.group(1)
        embed_url = f'https://player.vimeo.com/video/{video_id}'
        print(f"Vimeo -> Embed: {embed_url}")
        return embed_url

    vimeo_embed = r'(?:https?://)?(?:www\.)?player\.vimeo\.com/video/(\d+)'
    match = re.search(vimeo_embed, url)
    if match:
        video_id = match.group(1)
        embed_url = f'https://player.vimeo.com/video/{video_id}'
        print(f"Vimeo embed -> Keeping: {embed_url}")
        return embed_url

    print(f"No match found, returning original: {url}")
    return url

@register.filter
def can_embed_youtube(url):
    """
    Check if a YouTube video allows embedding using oEmbed API.
    """
    if not url or 'youtube' not in url and 'youtu.be' not in url:
        return True  # Assume non-YouTube videos can embed

    try:
        # Extract video ID
        video_id = None
        if 'youtube.com/watch' in url:
            video_id = re.search(r'v=([a-zA-Z0-9_-]+)', url)
        elif 'youtu.be/' in url:
            video_id = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)

        if video_id:
            video_id = video_id.group(1)

            # YouTube oEmbed endpoint
            oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
            response = requests.get(oembed_url, timeout=3)

            # If we get a successful response, embedding is allowed
            if response.status_code == 200:
                return True
            else:
                return False
    except:
        # If check fails, assume it can embed
        pass

    return True


# ===== NEW RECOMMENDATION TEMPLATE TAGS =====
@register.inclusion_tag('courses/recommendations.html', takes_context=True)
def render_recommendations(context, limit=3):
    """
    Template tag to display course recommendations.
    Usage: {% render_recommendations 3 %}
    """
    request = context.get('request')
    if request and request.user.is_authenticated:
        recommendations = get_course_recommendations(request.user, limit)
    else:
        # For anonymous users, get popular courses
        from ..recommendations import get_popular_courses
        recommendations = get_popular_courses(limit)

    return {'recommendations': recommendations, 'request': request}

@register.inclusion_tag('courses/next_course.html', takes_context=True)
def render_next_course_recommendation(context, current_course):
    """
    Template tag to display next course recommendation.
    Usage: {% render_next_course_recommendation course %}
    """
    request = context.get('request')
    if request and request.user.is_authenticated:
        next_courses = get_next_course_recommendation(request.user, current_course)
    else:
        next_courses = []

    return {'next_courses': next_courses, 'request': request}

@register.simple_tag
def recommendation_reason_badge(reason):
    """
    Returns a Bootstrap badge class based on recommendation reason.
    """
    reason_classes = {
        'Taken by learners like you': 'bg-primary',
        'Popular in your interests': 'bg-success',
        'Popular with learners': 'bg-info',
    }
    return reason_classes.get(reason, 'bg-secondary')

@register.inclusion_tag('courses/achievement_grid.html')
def render_achievements(user):
    """
    Display achievement gallery with progress.
    """
    from ..achievements import get_achievement_progress
    achievements = get_achievement_progress(user)
    return {'achievements': achievements}

@register.inclusion_tag('courses/recent_achievements.html')
def render_recent_achievements(user):
    """
    Display recently unlocked achievements.
    """
    from ..achievements import get_recent_achievements
    recent = get_recent_achievements(user)
    return {'recent_achievements': recent}
