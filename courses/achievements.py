# courses/achievements.py
from .models import Achievement, UserAchievement, XPEvent
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Sum


class AchievementCode:
    FIRST_LESSON = 'first-lesson'
    SECOND_LESSON = 'second-lesson'
    FIVE_LESSONS = 'five-lessons'
    TEN_LESSONS = 'ten-lessons'
    LESSON_MASTER = 'lesson-master'
    LESSON_GURU = 'lesson-guru'
    LESSON_LEGEND = 'lesson-legend'
    COURSE_COMPLETE = 'course-complete'

def get_achievement_by_code(code):
    """
    Get achievement by code with caching to reduce database queries.
    """
    cache_key = f'achievement_code_{code}'
    achievement = cache.get(cache_key)
    
    if not achievement:
        try:
            achievement = Achievement.objects.get(code=code)
            cache.set(cache_key, achievement, 3600)  # Cache for 1 hour
        except Achievement.DoesNotExist:
            return None
    
    return achievement

def check_and_award_achievement(user, achievement_code, request=None):
    """
    Check if a user has earned an achievement and award it if not already earned.
    Uses achievement code instead of name for reliability.
    
    Returns: (was_awarded, achievement)
    """
    achievement = get_achievement_by_code(achievement_code)
    
    if not achievement:
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
            points=achievement.xp_reward,
            reason=f"Achievement: {achievement.name}",
        )
        
        # Show message if request is provided
        if request:
            messages.success(
                request, 
                f"🏆 Achievement Unlocked: {achievement.name}!",
                extra_tags='achievement'
            )
        
        return True, achievement
    
    return False, achievement


# Pre-defined achievement checks
def check_course_completion_achievements(user, course, request=None):
    """
    Check for achievements related to course completion.
    Optimized to use fewer queries.
    """
    from .models import LessonCompletion, Lesson
    
    # Get total lessons count (cached per course)
    cache_key = f'course_lesson_count_{course.id}'
    total_lessons = cache.get(cache_key)
    
    if not total_lessons:
        total_lessons = Lesson.objects.filter(module__course=course).count()
        cache.set(cache_key, total_lessons, 3600)
    
    # Get completed count in one query
    completed_count = LessonCompletion.objects.filter(
        user=user,
        lesson__module__course=course
    ).count()
    
    achievements_awarded = []
    
    # First course completion
    if completed_count == total_lessons and total_lessons > 0:
        awarded, achievement = check_and_award_achievement(
            user, AchievementCode.COURSE_COMPLETE, request
        )
        if awarded:
            achievements_awarded.append(achievement)
    
    return achievements_awarded


def check_lesson_count_achievements(user, new_count=None, request=None):
    """
    Check for achievements based on total lessons completed across all courses.
    If new_count is provided, use it; otherwise calculate from database.
    
    Args:
        user: The user to check achievements for
        new_count: Optional pre-calculated lesson count (for efficiency)
        request: Optional request object for displaying messages
    """
    from .models import LessonCompletion
    
    # Use provided count or calculate from database
    if new_count is not None:
        total_completed = new_count
    else:
        # Get total completed lessons count with caching
        cache_key = f'user_lesson_count_{user.id}'
        total_completed = cache.get(cache_key)
        
        if not total_completed:
            total_completed = LessonCompletion.objects.filter(user=user).count()
            cache.set(cache_key, total_completed, 300)  # Cache for 5 minutes
    
    achievements_awarded = []
    
    # Map of thresholds to achievement codes
    threshold_map = [
        (1, AchievementCode.FIRST_LESSON),
        (2, AchievementCode.SECOND_LESSON),
        (5, AchievementCode.FIVE_LESSONS),
        (10, AchievementCode.TEN_LESSONS),
        (25, AchievementCode.LESSON_MASTER),
        (50, AchievementCode.LESSON_GURU),
        (100, AchievementCode.LESSON_LEGEND),
    ]
    
    # Check each threshold
    for threshold, code in threshold_map:
        if total_completed >= threshold:
            awarded, achievement = check_and_award_achievement(
                user, code, request
            )
            if awarded:
                achievements_awarded.append(achievement)
                # Special message for milestone achievements
                if request and threshold in [1, 2, 5, 10, 25, 50, 100]:
                    messages.success(
                        request,
                        f"🎯 Milestone: You've completed {total_completed} lessons!",
                        extra_tags='milestone'
                    )
    
    return achievements_awarded


def get_user_achievements(user):
    """
    Get all achievements for a user with unlocked status.
    Useful for profile pages.
    """
    all_achievements = Achievement.objects.all().order_by('xp_reward')
    user_achievements = set(
        UserAchievement.objects.filter(user=user)
        .values_list('achievement_id', flat=True)
    )
    
    achievements_data = []
    for achievement in all_achievements:
        achievements_data.append({
            'achievement': achievement,
            'unlocked': achievement.id in user_achievements,
            'unlocked_at': None,  # You can fetch this if needed
        })
    
    return achievements_data

def get_achievement_progress(user):
    """
    Calculate progress for all achievements for a user.
    Returns list of achievements with current progress and status.
    """
    from .models import LessonCompletion, Course, XPEvent
    
    achievements = Achievement.objects.all().order_by('category', 'threshold')
    user_achievements = set(
        UserAchievement.objects.filter(user=user)
        .values_list('achievement_id', flat=True)
    )
    
    # Calculate user stats once for efficiency
    total_lessons = LessonCompletion.objects.filter(user=user).count()
    total_courses = Course.objects.filter(enrollments__user=user).count()
    total_xp = XPEvent.objects.filter(user=user).aggregate(total=Sum('points'))['total'] or 0
    
    progress_data = []
    
    for achievement in achievements:
        # Calculate current progress based on category
        if achievement.category == 'lessons':
            current = total_lessons
        elif achievement.category == 'courses':
            current = total_courses
        elif achievement.category == 'xp':
            current = total_xp
        else:
            current = 0
        
        # Calculate percentage
        if achievement.threshold > 0:
            percentage = min(100, int((current / achievement.threshold) * 100))
        else:
            percentage = 100 if achievement.id in user_achievements else 0
        
        progress_data.append({
            'achievement': achievement,
            'unlocked': achievement.id in user_achievements,
            'current': current,
            'threshold': achievement.threshold,
            'percentage': percentage,
            'remaining': max(0, achievement.threshold - current) if not achievement.id in user_achievements else 0,
        })
    
    return progress_data

def get_recent_achievements(user, limit=5):
    """Get recently unlocked achievements."""
    return UserAchievement.objects.filter(user=user).select_related('achievement').order_by('-unlocked_at')[:limit]

def check_streak_achievements(user, current_streak, request=None):
    """
    Check for achievements based on streak milestones.
    This function checks ALL achievements with streak-related categories.
    """
    from .models import Achievement, UserAchievement, XPEvent
    
    # Find all achievements that might be streak-related
    # Look for achievements with category containing 'streak' (case insensitive)
    streak_categories = ['streak', 'Learning Streak', 'Streak', 'learning streak']
    
    possible_achievements = Achievement.objects.filter(
        threshold__lte=current_streak
    ).filter(
        category__in=streak_categories
    )
    
    # Also include achievements with threshold=1 that might be first streak
    if current_streak >= 1:
        first_streak_achievements = Achievement.objects.filter(
            threshold=1,
            category__in=streak_categories + ['', None]  # Include empty categories too
        )
        possible_achievements = possible_achievements | first_streak_achievements
    
    achievements_awarded = []
    
    for achievement in possible_achievements.distinct():
        # Check if user already has this achievement
        already_has = UserAchievement.objects.filter(
            user=user,
            achievement=achievement
        ).exists()
        
        if not already_has and current_streak >= achievement.threshold:
            # Award the achievement
            UserAchievement.objects.create(user=user, achievement=achievement)
            
            # Award XP
            XPEvent.objects.create(
                user=user,
                points=achievement.xp_reward,
                reason=f"Achievement: {achievement.name}",
            )
            
            if request:
                messages.success(
                    request,
                    f"🔥 Achievement Unlocked: {achievement.name}! +{achievement.xp_reward} XP",
                    extra_tags='achievement'
                )
            
            achievements_awarded.append(achievement)
            print(f"Awarded streak achievement: {achievement.name} to {user.email}")  # Debug
            
    return achievements_awarded