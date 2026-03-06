# courses/achievements.py
from .models import Achievement, UserAchievement, XPEvent
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Sum
from django.apps import apps

# Helper functions to safely get models (prevents circular imports)
def get_lesson_completion_model():
    return apps.get_model('courses', 'LessonCompletion')

def get_course_model():
    return apps.get_model('courses', 'Course')

def get_lesson_model():
    return apps.get_model('courses', 'Lesson')

def get_learning_streak_model():
    return apps.get_model('courses', 'LearningStreak')

class AchievementCode:
    # Lesson completion achievements
    FIRST_LESSON = 'first-lesson'
    SECOND_LESSON = 'second-lesson'
    FIFTH_LESSON = 'fifth-lesson'
    TENTH_LESSON = 'tenth-lesson'
    TWENTY_FIFTH_LESSON = 'twenty-fifth-lesson'
    FIFTIETH_LESSON = 'fiftieth-lesson'
    HUNDREDTH_LESSON = 'hundredth-lesson'

    # Course completion achievements
    FIRST_COURSE = 'first-course'
    THIRD_COURSE = 'third-course'
    FIFTH_COURSE = 'fifth-course'
    TENTH_COURSE = 'tenth-course'

    # Streak achievements
    THREE_DAY_STREAK = 'three-day-streak'
    WEEK_STREAK = 'week-streak'
    TWO_WEEK_STREAK = 'two-week-streak'
    MONTH_STREAK = 'month-streak'
    TWO_MONTH_STREAK = 'two-month-streak'

    # XP achievements
    HUNDRED_XP = 'hundred-xp'
    FIVE_HUNDRED_XP = 'five-hundred-xp'
    THOUSAND_XP = 'thousand-xp'
    FIVE_THOUSAND_XP = 'five-thousand-xp'

    # Social achievements
    FIRST_COMMENT = 'first-comment'
    TEN_COMMENTS = 'ten-comments'
    FIRST_UPVOTE_RECEIVED = 'first-upvote-received'
    HELPFUL_REVIEW = 'helpful-review'

    # Special achievements
    EARLY_BIRD = 'early-bird'
    NIGHT_OWL = 'night-owl'
    WEEKEND_LEARNER = 'weekend-learner'
    PERFECT_WEEK = 'perfect-week'

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
    Now checks for multiple course milestones (1st, 3rd, 5th, 10th course).
    """
    Lesson = get_lesson_model()
    LessonCompletion = get_lesson_completion_model()
    Course = get_course_model()

    # Get total lessons count for this course
    total_lessons = Lesson.objects.filter(module__course=course).count()

    # Check if user just completed this course
    completed_count = LessonCompletion.objects.filter(
        user=user,
        lesson__module__course=course
    ).count()

    achievements_awarded = []

    # If they just completed this course
    if completed_count == total_lessons and total_lessons > 0:
        # Count how many TOTAL courses they've completed
        completed_courses_count = 0

        # Get all courses the user is enrolled in
        enrolled_courses = Course.objects.filter(enrollments__user=user)

        for enrolled_course in enrolled_courses:
            course_total = Lesson.objects.filter(module__course=enrolled_course).count()
            course_completed = LessonCompletion.objects.filter(
                user=user,
                lesson__module__course=enrolled_course
            ).count()

            if course_completed == course_total and course_total > 0:
                completed_courses_count += 1

        # Check each threshold
        if completed_courses_count >= 1:
            awarded, achievement = check_and_award_achievement(
                user, AchievementCode.FIRST_COURSE, request
            )
            if awarded:
                achievements_awarded.append(achievement)

        if completed_courses_count >= 3:
            awarded, achievement = check_and_award_achievement(
                user, AchievementCode.THIRD_COURSE, request
            )
            if awarded:
                achievements_awarded.append(achievement)

        if completed_courses_count >= 5:
            awarded, achievement = check_and_award_achievement(
                user, AchievementCode.FIFTH_COURSE, request
            )
            if awarded:
                achievements_awarded.append(achievement)

        if completed_courses_count >= 10:
            awarded, achievement = check_and_award_achievement(
                user, AchievementCode.TENTH_COURSE, request
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
    LessonCompletion = get_lesson_completion_model()

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
        (5, AchievementCode.FIFTH_LESSON),
        (10, AchievementCode.TENTH_LESSON),
        (25, AchievementCode.TWENTY_FIFTH_LESSON),
        (50, AchievementCode.FIFTIETH_LESSON),
        (100, AchievementCode.HUNDREDTH_LESSON),
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
    LessonCompletion = get_lesson_completion_model()
    Course = get_course_model()
    LearningStreak = get_learning_streak_model()

    achievements = Achievement.objects.all().order_by('category', 'threshold')
    user_achievements = set(
        UserAchievement.objects.filter(user=user)
        .values_list('achievement_id', flat=True)
    )

    # Calculate user stats once for efficiency
    total_lessons = LessonCompletion.objects.filter(user=user).count()
    total_courses = Course.objects.filter(enrollments__user=user).count()
    total_xp = XPEvent.objects.filter(user=user).aggregate(total=Sum('points'))['total'] or 0

    # Get user's current streak
    try:
        streak = LearningStreak.objects.get(user=user)
        current_streak = streak.current_streak
    except LearningStreak.DoesNotExist:
        current_streak = 0

    progress_data = []

    for achievement in achievements:
        # Calculate current progress based on category
        if achievement.category == 'lessons':
            current = total_lessons
        elif achievement.category == 'courses':
            current = total_courses
        elif achievement.category == 'xp':
            current = total_xp
        elif achievement.category == 'streak':
            current = current_streak
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
            'remaining': max(0, achievement.threshold - current) if achievement.id not in user_achievements else 0,
        })

    return progress_data

def get_recent_achievements(user, limit=5):
    """Get recently unlocked achievements."""
    return UserAchievement.objects.filter(user=user).select_related('achievement').order_by('-unlocked_at')[:limit]

def check_streak_achievements(user, current_streak, request=None):
    """
    Check for achievements based on streak milestones.
    """
    # Keep these prints for now - they're useful for debugging
    print(f"\n=== CHECKING STREAK ACHIEVEMENTS ===")
    print(f"User: {user.email}")
    print(f"Current streak: {current_streak}")

    # Define streak milestones and their achievement codes
    streak_milestones = [
        (3, AchievementCode.THREE_DAY_STREAK, '3-Day Streak', 30),
        (7, AchievementCode.WEEK_STREAK, 'Week Warrior', 70),
        (14, AchievementCode.TWO_WEEK_STREAK, 'Two-Week Dedication', 150),
        (30, AchievementCode.MONTH_STREAK, 'Monthly Master', 300),
        (60, AchievementCode.TWO_MONTH_STREAK, 'Two-Month Champion', 500),
    ]

    achievements_awarded = []

    for threshold, code, name, xp in streak_milestones:
        print(f"Checking threshold: {threshold} days (code: {code})")

        if current_streak >= threshold:
            print(f"  ✓ User qualifies for {name}")

            # Check if achievement exists, create if not
            try:
                achievement = Achievement.objects.get(code=code)
                print(f"  ✓ Achievement found in database")
            except Achievement.DoesNotExist:
                print(f"  ✗ Achievement not found, creating...")
                achievement = Achievement.objects.create(
                    code=code,
                    name=name,
                    description=f'Maintain a {threshold}-day learning streak',
                    xp_reward=xp,
                    icon='🔥' if threshold < 14 else '⚡' if threshold < 30 else '👑',
                    category='streak',
                    threshold=threshold
                )
                print(f"  ✓ Created achievement: {name}")

            # Check if user already has this achievement
            already_has = UserAchievement.objects.filter(
                user=user,
                achievement=achievement
            ).exists()

            if not already_has:
                print(f"  ✓ Awarding achievement to user")
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
            else:
                print(f"  - User already has this achievement")
        else:
            print(f"  - Does not qualify for {threshold} days (need {threshold}, have {current_streak})")

    print(f"=== STREAK CHECK COMPLETE ===\n")
    return achievements_awarded


def check_early_bird_achievements(user, lesson_completed_at, request=None):
    """
    Check if user qualifies for Early Bird achievement.
    """
    LessonCompletion = get_lesson_completion_model()
    from datetime import time

    # Check if lesson was completed before 9 AM
    if lesson_completed_at.time() < time(9, 0):  # 9:00 AM
        # Count how many early lessons user has
        early_lessons = LessonCompletion.objects.filter(
            user=user,
            completed_at__time__lt=time(9, 0)
        ).count()

        # Check if they hit the threshold
        if early_lessons >= 2:
            awarded, achievement = check_and_award_achievement(
                user, 'early-bird', request
            )
            return awarded

    return False
