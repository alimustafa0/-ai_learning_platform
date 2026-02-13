# courses/recommendations.py
from .models import Category, Course, Enrollment, LessonCompletion
from django.db.models import Count, Q
from collections import Counter
import random

def get_course_recommendations(user, limit=3):
    """
    Recommend courses for a user based on:
    1. What similar users are taking (collaborative filtering)
    2. Popular courses in categories they've shown interest in
    3. Courses appropriate for their level
    """
    if not user.is_authenticated:
        # For anonymous users, show popular courses
        return get_popular_courses(limit)
    
    # Get courses user is already enrolled in or completed
    enrolled_course_ids = set(
        Enrollment.objects.filter(user=user)
        .values_list('course_id', flat=True)
    )
    
    # Get categories user has shown interest in
    interested_categories = get_user_interested_categories(user)
    
    # Get courses taken by similar users
    similar_users_courses = get_courses_from_similar_users(user, enrolled_course_ids)
    
    # Get popular courses in interested categories
    category_courses = get_category_courses(interested_categories, enrolled_course_ids)
    
    # Combine and score recommendations
    recommendations = []
    
    # Add similar users courses (higher weight)
    for course in similar_users_courses:
        recommendations.append({
            'course': course,
            'score': 3,
            'reason': f"Taken by learners like you"
        })
    
    # Add category courses (medium weight)
    for course in category_courses:
        # Check if already added
        if not any(r['course'].id == course.id for r in recommendations):
            recommendations.append({
                'course': course,
                'score': 2,
                'reason': f"Popular in {course.categories.first().name if course.categories.exists() else 'your interests'}"
            })
    
    # Sort by score and return top N
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    # If we don't have enough, add popular courses
    if len(recommendations) < limit:
        popular = get_popular_courses(limit * 2)
        for item in popular:
            if not any(r['course'].id == item['course'].id for r in recommendations):
                recommendations.append(item)
    
    return recommendations[:limit]

def get_user_interested_categories(user):
    """
    Determine which categories a user is interested in based on:
    - Courses they've enrolled in
    - Lessons they've completed
    """
    # Get categories from enrolled courses
    enrolled_categories = Category.objects.filter(
        courses__enrollments__user=user
    ).annotate(
        count=Count('courses')
    ).order_by('-count')
    
    # Get categories from completed lessons
    completed_categories = Category.objects.filter(
        courses__modules__lessons__completions__user=user
    ).annotate(
        count=Count('courses')
    ).order_by('-count')
    
    # Combine and return unique categories
    interested = list(enrolled_categories) + list(completed_categories)
    return list(set(interested))[:5]  # Top 5 categories

def get_courses_from_similar_users(user, exclude_course_ids):
    """
    Find users with similar enrollment patterns and see what they're taking.
    """
    # Find users who took at least one course this user took
    user_courses = Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    
    if not user_courses:
        return []
    
    similar_users = Enrollment.objects.filter(
        course_id__in=user_courses
    ).exclude(
        user=user
    ).values_list('user_id', flat=True).distinct()
    
    # Get courses those similar users are taking
    recommended_courses = Course.objects.filter(
        enrollments__user__in=similar_users,
        is_published=True
    ).exclude(
        id__in=exclude_course_ids
    ).annotate(
        popularity=Count('enrollments')
    ).order_by('-popularity')[:10]
    
    return list(recommended_courses)

def get_category_courses(categories, exclude_course_ids):
    """
    Get popular courses in given categories.
    """
    if not categories:
        return []
    
    return Course.objects.filter(
        categories__in=categories,
        is_published=True
    ).exclude(
        id__in=exclude_course_ids
    ).annotate(
        popularity=Count('enrollments')
    ).order_by('-popularity')[:10]

def get_popular_courses(limit=3):
    """
    Get most enrolled courses overall.
    """
    popular = Course.objects.filter(
        is_published=True
    ).annotate(
        enrollment_count=Count('enrollments')
    ).order_by('-enrollment_count')[:limit * 2]
    
    return [{
        'course': course,
        'score': 1,
        'reason': 'Popular with learners'
    } for course in popular]

def get_next_course_recommendation(user, current_course):
    """
    Recommend the next course based on what users typically take after this one.
    """
    # Find users who completed this course
    users_completed = User.objects.filter(
        lessoncompletion__lesson__module__course=current_course
    ).distinct()
    
    # See what courses they took next
    next_courses = Course.objects.filter(
        enrollments__user__in=users_completed,
        is_published=True
    ).exclude(
        id=current_course.id
    ).annotate(
        count=Count('enrollments')
    ).order_by('-count')[:3]
    
    return next_courses