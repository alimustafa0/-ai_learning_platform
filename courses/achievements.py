# courses/achievements.py
from .models import Achievement, UserAchievement, XPEvent
from django.contrib import messages

def check_and_award_achievement(user, achievement_name, request=None):
    """
    Check if a user has earned an achievement and award it if not already earned.
    Optionally display a message via request.
    
    Returns: (was_awarded, achievement)
    """
    try:
        achievement = Achievement.objects.get(name=achievement_name)
    except Achievement.DoesNotExist:
        # Achievement doesn't exist yet
        return False, None
    
    # Check if user already has this achievement
    already_has = UserAchievement.objects.filter(
        user=user, 
        achievement=achievement
    ).exists()
    
    if not already_has:
        # Award the achievement
        UserAchievement.objects.create(user=user, achievement=achievement)
        
        # Award XP for earning achievement
        XPEvent.objects.create(
            user=user,
            points=achievement.xp_reward if hasattr(achievement, 'xp_reward') else 50,
            reason=f"Achievement: {achievement.name}",
        )
        
        # Show message if request is provided
        if request:
            messages.success(request, f"🏆 Achievement Unlocked: {achievement.name}!")
        
        return True, achievement
    
    return False, achievement


# Pre-defined achievement checks
def check_course_completion_achievements(user, course, request=None):
    """
    Check for achievements related to course completion.
    """
    from .models import LessonCompletion, Lesson
    
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_count = LessonCompletion.objects.filter(
        user=user,
        lesson__module__course=course
    ).count()
    
    achievements_awarded = []
    
    # First course completion
    if completed_count == total_lessons and total_lessons > 0:
        awarded, achievement = check_and_award_achievement(
            user, "Course Complete", request
        )
        if awarded:
            achievements_awarded.append(achievement)
    
    return achievements_awarded


def check_lesson_count_achievements(user, new_count, request=None):
    """
    Check for achievements based on total lessons completed across all courses.
    """
    from .models import LessonCompletion
    
    achievements_awarded = []
    achievement_map = {
        1: "First Lesson",
        5: "Five Lessons",
        10: "Ten Lessons",
        25: "Lesson Master",
        50: "Lesson Guru",
        100: "Lesson Legend",
    }
    
    if new_count in achievement_map:
        awarded, achievement = check_and_award_achievement(
            user, achievement_map[new_count], request
        )
        if awarded:
            achievements_awarded.append(achievement)
    
    return achievements_awarded