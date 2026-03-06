# users/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, UserProfileForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Sum
from courses.models import Course, Lesson, LessonCompletion, Review, UserAchievement, XPEvent, LearningStreak
from courses.gamification import get_level_progress
from .models import Follow

User = get_user_model()

def signup(request):
    """
    Handle user registration.
    """
    # If user is already authenticated, redirect them
    if request.user.is_authenticated:
        return redirect('course_list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Add welcome message
            from django.contrib import messages
            messages.success(request, f'Welcome to AI Learning Platform, {user.first_name}!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/signup.html', {'form': form})

@login_required
def profile_view(request):
    """
    Display user profile information.
    """
    return render(request, 'users/profile.html', {'profile_user': request.user})

# === ADD THIS NEW VIEW ===
@login_required
def profile_edit(request):
    """
    Allow users to edit their profile information.
    """
    if request.method == 'POST':
        form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=request.user
        )
        if form.is_valid():
            form.save()
            from django.contrib import messages
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile_view')  # Redirect to view profile
        else:
            # If form is invalid, show error message
            from django.contrib import messages
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'users/profile_edit.html', {'form': form})

def public_profile(request, username):
    """
    Public view of a user's profile.
    """
    # Get user by email (since username is None in your User model)
    user = get_object_or_404(User, email=username)

    # Get user stats
    total_xp = XPEvent.objects.filter(user=user).aggregate(total=Sum('points'))['total'] or 0
    current_level, _ = get_level_progress(total_xp)

    # Get achievements
    achievements = UserAchievement.objects.filter(user=user).select_related('achievement').order_by('-unlocked_at')[:6]
    unlocked_ids = [ua.achievement_id for ua in achievements]

    # Get courses in progress - FIXED THIS PART
    enrollments = user.enrollments.select_related('course')
    courses_data = []
    for enrollment in enrollments:
        course = enrollment.course

        # Get total lessons count for this course
        total_lessons = Lesson.objects.filter(module__course=course).count()

        # Get completed lessons count for this user in this course
        completed = LessonCompletion.objects.filter(
            user=user,
            lesson__module__course=course
        ).count()

        progress = 0
        if total_lessons > 0:
            progress = int((completed / total_lessons) * 100)

        courses_data.append({
            'course': course,
            'progress': progress,
            'completed': completed == total_lessons and total_lessons > 0
        })

    # Get streak info
    try:
        streak = LearningStreak.objects.get(user=user)
    except LearningStreak.DoesNotExist:
        streak = None

    # Check if current user follows this profile
    is_following = False
    followers_count = 0
    following_count = 0

    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user,
            following=user
        ).exists()

    # Get follower/following counts
    followers_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()

    # Get recent activity (last 5 completed lessons)
    recent_activity = LessonCompletion.objects.filter(
        user=user
    ).select_related('lesson', 'lesson__module__course').order_by('-completed_at')[:5]

    context = {
        'profile_user': user,
        'total_xp': total_xp,
        'level_number': current_level[0],
        'level_title': current_level[1],
        'achievements': achievements,
        'unlocked_ids': unlocked_ids,
        'courses_data': courses_data,
        'streak': streak,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'recent_activity': recent_activity,
        'is_own_profile': request.user.is_authenticated and request.user.id == user.id,
    }

    return render(request, 'users/public_profile.html', context)

@login_required
@require_POST
def toggle_follow(request, user_id):
    """
    Follow or unfollow a user.
    """
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        return JsonResponse({
            'status': 'error',
            'message': 'You cannot follow yourself'
        }, status=400)

    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )

    if not created:
        # Already following, so unfollow
        follow.delete()
        is_following = False
        message = f"You unfollowed {target_user.get_full_name() or target_user.email}"
    else:
        is_following = True
        message = f"You are now following {target_user.get_full_name() or target_user.email}"

        # Award XP for following (small bonus)
        XPEvent.objects.create(
            user=request.user,
            points=1,
            reason=f"Followed {target_user.email[:30]}"
        )

    # Get updated counts
    followers_count = Follow.objects.filter(following=target_user).count()
    following_count = Follow.objects.filter(follower=target_user).count()

    return JsonResponse({
        'status': 'success',
        'is_following': is_following,
        'message': message,
        'followers_count': followers_count,
        'following_count': following_count,
    })

@login_required
def following_list(request):
    """
    Show users the current user is following.
    """
    follows = Follow.objects.filter(follower=request.user).select_related('following')
    users = [follow.following for follow in follows]

    return render(request, 'users/following_list.html', {
        'users': users,
        'count': len(users)
    })

@login_required
def followers_list(request):
    """
    Show users following the current user.
    """
    follows = Follow.objects.filter(following=request.user).select_related('follower')
    users = [follow.follower for follow in follows]

    # Get IDs of users that the current user is following
    following_ids = set()
    if request.user.is_authenticated:
        following_ids = set(Follow.objects.filter(
            follower=request.user
        ).values_list('following_id', flat=True))

    return render(request, 'users/followers_list.html', {
        'users': users,
        'count': len(users),
        'following_ids': following_ids,  # Pass this to template
    })

@login_required
def activity_feed(request):
    """
    Show activity feed of users the current user follows.
    """
    # Get users this user follows
    following_ids = set(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))

    # Get recent activities from followed users
    recent_completions = LessonCompletion.objects.filter(
        user_id__in=following_ids
    ).select_related(
        'user', 'lesson', 'lesson__module__course'
    ).order_by('-completed_at')[:20]

    recent_achievements = UserAchievement.objects.filter(
        user_id__in=following_ids
    ).select_related(
        'user', 'achievement'
    ).order_by('-unlocked_at')[:20]

    recent_reviews = Review.objects.filter(
        user_id__in=following_ids
    ).select_related(
        'user', 'course'
    ).order_by('-created_at')[:20]

    # Combine and sort activities
    activities = []

    for completion in recent_completions:
        activities.append({
            'type': 'lesson',
            'user': completion.user,
            'user_id': completion.user.id,
            'time': completion.completed_at,
            'data': completion,
            'icon': '📚',
            'text': f"completed a lesson: {completion.lesson.title}",
            'course': completion.lesson.module.course,
        })

    for achievement in recent_achievements:
        activities.append({
            'type': 'achievement',
            'user': achievement.user,
            'user_id': achievement.user.id,
            'time': achievement.unlocked_at,
            'data': achievement,
            'icon': achievement.achievement.icon or '🏆',
            'text': f"unlocked achievement: {achievement.achievement.name}",
        })

    for review in recent_reviews:
        activities.append({
            'type': 'review',
            'user': review.user,
            'user_id': review.user.id,
            'time': review.created_at,
            'data': review,
            'icon': '⭐',
            'text': f"reviewed {review.course.title}",
            'rating': review.rating,
        })

    # Sort by time (newest first)
    activities.sort(key=lambda x: x['time'], reverse=True)

    return render(request, 'users/activity_feed.html', {
        'activities': activities[:30],
        'following_ids': following_ids,
    })
