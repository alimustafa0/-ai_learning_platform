# courses/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def send_comment_notification_async(parent_comment, reply_comment, replier):
    """
    Send email notification when someone replies to a comment.
    This function is meant to be called in a background thread.
    """
    try:
        if not parent_comment.user.email:
            return
        
        subject = f"Someone replied to your comment on {reply_comment.lesson.title}"
        
        lesson_url = settings.SITE_URL + reverse('lesson_detail', args=[reply_comment.lesson.id])
        
        context = {
            'parent_comment': parent_comment,
            'reply_comment': reply_comment,
            'replier': replier,
            'lesson_url': lesson_url,
        }
        
        html_message = render_to_string('courses/email/comment_reply.html', context)
        plain_message = render_to_string('courses/email/comment_reply.txt', context)
        
        # Send email - this might still be slow but it's in a thread now
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [parent_comment.user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        # Log error but don't crash
        logger.error(f"Failed to send reply notification: {e}")