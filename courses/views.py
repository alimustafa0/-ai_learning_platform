from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from config import settings as setting
from .models import Course, Enrollment, Lesson, LessonCompletion, Review, XPEvent, Achievement, UserAchievement, Payment, Comment, Certificate, LearningStreak, LearningActivity
from .forms import CommentForm, ReviewForm
from .gamification import get_level_progress
from .achievements import check_early_bird_achievements, check_lesson_count_achievements, check_course_completion_achievements
import time
import stripe
from django.conf import settings
from django.urls import reverse
from users.models import User
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from weasyprint import HTML
import tempfile
from datetime import date, datetime



# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def course_list(request):
    courses = Course.objects.filter(is_published=True)

    # calculate user level
    if request.user.is_authenticated:
        total_xp = XPEvent.objects.filter(user=request.user).aggregate(
            Sum("points")
        )["points__sum"] or 0

        current_level, _ = get_level_progress(total_xp)
        user_level_number = current_level[0]
    else:
        user_level_number = 0
    return render(request, "courses/course_list.html", {"courses": courses, "user_level_number": user_level_number})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_published=True)

    # Check if user is authenticated before calculating XP/level
    if request.user.is_authenticated:
        total_xp = XPEvent.objects.filter(user=request.user).aggregate(total=Sum('points'))['total'] or 0
        current_level, next_level = get_level_progress(total_xp)
        user_level_number = current_level[0]
        
        # Check if user is enrolled in this course
        is_enrolled = Enrollment.objects.filter(
            user=request.user, 
            course=course
        ).exists()
        
        # Get user's review if it exists
        user_review = course.reviews.filter(user=request.user).first()
        
        # Get completed lessons for this course
        completed_lessons = []
        completed_count = 0
        total_lessons = 0
        progress_percentage = 0
        
        if is_enrolled:
            completed_lessons = LessonCompletion.objects.filter(
                user=request.user,
                lesson__module__course=course
            ).values_list('lesson_id', flat=True)
            
            completed_count = len(completed_lessons)
            total_lessons = Lesson.objects.filter(module__course=course).count()
            
            if total_lessons > 0:
                progress_percentage = int((completed_count / total_lessons) * 100)
        
        # Get IDs of reviews this user found helpful
        user_helpful_review_ids = []
        if request.user.is_authenticated:
            user_helpful_review_ids = Review.objects.filter(
                helpful_votes=request.user
            ).values_list('id', flat=True)

        # Get users the current user follows
        following_ids = set()
        if request.user.is_authenticated:
            from users.models import Follow
            following_ids = set(Follow.objects.filter(
                follower=request.user
            ).values_list('following_id', flat=True))
            
    else:
        # For anonymous users
        user_level_number = 0
        is_enrolled = False
        user_review = None
        completed_lessons = []
        completed_count = 0
        total_lessons = Lesson.objects.filter(module__course=course).count()
        progress_percentage = 0
        user_helpful_review_ids = []
        following_ids = set()

    # Level lock check (only if required_level > 1)
    if user_level_number < course.required_level:
        return render(request, "courses/level_locked.html", {
            "course": course,
            "required_level": course.required_level,
            "user_level_number": user_level_number,
            "following_ids": following_ids,
        })
    
    # Get rating distribution
    distribution = course.rating_distribution()
    
    return render(request, "courses/course_detail.html", {
        "course": course,
        "user_level_number": user_level_number,
        "is_enrolled": is_enrolled,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "completed_count": completed_count,  # Add this
        "progress_percentage": progress_percentage,  # Add this
        "user_review": user_review,
        "distribution": distribution,
        "user_helpful_review_ids": user_helpful_review_ids,  # Add this for helpful button
    })

@login_required
def enroll_course(request, course_id):
    """
    Enroll the current user in a course.
    For free courses: enroll directly.
    For paid courses: redirect to checkout.
    """
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, f"You are already enrolled in '{course.title}'.")
        return redirect('course_detail', course_id=course.id)
    
    # Check if course is free
    if course.is_free():
        # Free course: enroll directly
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )
        
        if created:
            messages.success(request, f"You have successfully enrolled in '{course.title}'!")
            # Award XP for enrollment
            XPEvent.objects.create(
                user=request.user,
                points=25,
                reason=f"Enrolled in course: {course.title}",
            )
        return redirect('course_detail', course_id=course.id)
    else:
        # Paid course: redirect to checkout
        messages.info(request, f"'{course.title}' is a paid course. Please complete payment to enroll.")
        return redirect('course_checkout', course_id=course.id)

@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    html_content = lesson.content

    # previous lesson
    previous_lesson = Lesson.objects.filter(
        module=lesson.module,
        order__lt=lesson.order
    ).order_by("-order").first()

    # next lesson
    next_lesson = Lesson.objects.filter(
        module=lesson.module,
        order__gt=lesson.order
    ).order_by("order").first()

    course = lesson.module.course
    is_enrolled = course.enrollments.filter(user=request.user).exists()

    if not is_enrolled:
        return render(request, "courses/not_enrolled.html", {"course": course})
    
    is_completed = LessonCompletion.objects.filter(user=request.user, lesson=lesson).exists()
    completed_lessons = LessonCompletion.objects.filter(user=request.user, lesson__module__course=course).values_list("lesson_id", flat=True)
    
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_count = len(completed_lessons)
    progress_percentage = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

    # ===== PAGINATED COMMENTS =====
    # Get top-level comments only, ordered by creation date (newest first)
    comments_list = lesson.comments.filter(parent=None).select_related(
        'user'
    ).prefetch_related(
        'replies__user',
        'replies__upvotes'
    ).order_by('-created_at')
    
    # Paginate comments - show 5 per page initially
    page = request.GET.get('comments_page', 1)
    paginator = Paginator(comments_list, 5)  # Show 5 comments per page
    
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)
    
    # Check which comments the user has upvoted (for all comments on this page)
    user_upvoted_comment_ids = set()
    if request.user.is_authenticated:
        # Collect all comment IDs from current page and their replies
        comment_ids = [c.id for c in comments]
        for comment in comments:
            comment_ids.extend([r.id for r in comment.replies.all()])
        
        user_upvoted = Comment.upvotes.through.objects.filter(
            comment_id__in=comment_ids,
            user_id=request.user.id
        ).values_list('comment_id', flat=True)
        user_upvoted_comment_ids = set(user_upvoted)

    following_ids = set()
    if request.user.is_authenticated:
        from users.models import Follow
        following_ids = set(Follow.objects.filter(
            follower=request.user
        ).values_list('following_id', flat=True))
    
    comment_form = CommentForm()
    
    if request.method == 'POST' and 'comment_submit' in request.POST:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.lesson = lesson
            comment.user = request.user
            comment.save()
            messages.success(request, "Your comment has been posted!")
            return redirect('lesson_detail', lesson_id=lesson.id)
    
    return render(request, "courses/lesson_detail.html", {
        "lesson": lesson,
        "content": html_content,
        "previous_lesson": previous_lesson,
        "next_lesson": next_lesson,
        "course": course,
        "is_completed": is_completed,
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
        "completed_count": completed_count,
        "progress_percentage": progress_percentage,
        "comments": comments,  # Now this is a Page object, not a queryset
        "comment_form": comment_form,
        "user_upvoted_comment_ids": user_upvoted_comment_ids,
        "total_comments": lesson.comments.count(),
        "following_ids": following_ids,
    })

@login_required
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    # 1. Check current XP BEFORE adding new points
    xp_before = XPEvent.objects.filter(user=request.user).aggregate(Sum('points'))['points__sum'] or 0
    level_before, _ = get_level_progress(xp_before)

    # security gate again
    is_enrolled = course.enrollments.filter(user=request.user).exists()
    if not is_enrolled:
        return render(request, "courses/not_enrolled.html", {"course": course})

    # create completion if not exists
    completion, created = LessonCompletion.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )

    # grant XP (avoid duplicates) - only if newly created
    if created:
        XPEvent.objects.create(
            user=request.user,
            points=10,
            reason=f"Completed lesson: {lesson.title}",
        )
        
        # ===== UPDATED: Update streak and activity with request =====
        from datetime import date
        today = date.today()
        
        # Get or create streak
        streak, _ = LearningStreak.objects.get_or_create(user=request.user)
        streak.update_streak(today, request)  # This will call check_streak_achievements
        
        # Update daily activity
        activity, _ = LearningActivity.objects.get_or_create(
            user=request.user,
            date=today
        )
        activity.count += 1
        activity.xp_earned += 10
        activity.save()

        # Check for Early Bird achievement
        from datetime import datetime
        check_early_bird_achievements(request.user, datetime.now(), request)

    # Calculate total completed lessons count
    total_completed = LessonCompletion.objects.filter(user=request.user).count()
    
    # Check for lesson count achievements (1st, 5th, 10th lesson etc.)
    check_lesson_count_achievements(request.user, total_completed, request)
    
    # Check for course completion achievements
    check_course_completion_achievements(request.user, course, request)

    # 4. Check XP AFTER adding points
    xp_after = XPEvent.objects.filter(user=request.user).aggregate(Sum('points'))['points__sum'] or 0
    level_after, _ = get_level_progress(xp_after)

    # 5. Compare: Did we Level Up?
    if level_after[0] > level_before[0]:
        messages.success(
            request, 
            f"🎉 LEVEL UP! You reached Level {level_after[0]} - {level_after[1]}!"
        )

    # find next lesson in order
    next_lesson = Lesson.objects.filter(
        module__course=course,
        module__order__gte=lesson.module.order,
    ).order_by("module__order", "order")

    found_current = False
    for item in next_lesson:
        if found_current:
            return redirect("lesson_detail", lesson_id=item.id)
        if item.id == lesson.id:
            found_current = True

    # no next lesson → course finished
    return redirect("course_completed", course_id=course.id)

@login_required
def dashboard(request):
    from .recommendations import get_course_recommendations

    recommendations = get_course_recommendations(request.user, limit=3)
    
    # Calculate user stats
    total_xp = XPEvent.objects.filter(user=request.user).aggregate(total=Sum('points'))['total'] or 0
    current_level, next_level = get_level_progress(total_xp)
    
    level_number, level_title, level_xp = current_level
    
    if next_level:
        next_level_number, next_level_title, next_level_xp = next_level
        xp_into_level = total_xp - level_xp
        xp_range = next_level_xp - level_xp
        level_progress_percent = int((xp_into_level / xp_range) * 100) if xp_range > 0 else 0
    else:
        next_level_title = "MAX"
        level_progress_percent = 100
    
    # Get all achievements
    all_achievements = Achievement.objects.all()
    unlocked_ids = UserAchievement.objects.filter(
        user=request.user
    ).values_list("achievement_id", flat=True)

    # Get achievement progress
    from .achievements import get_achievement_progress, get_recent_achievements
    achievement_progress = get_achievement_progress(request.user)
    recent_achievements = get_recent_achievements(request.user)
    
    # Get enrollments and course progress
    enrollments = request.user.enrollments.select_related("course")
    course_data = []
    in_progress_courses = []
    completed_courses = []
    
    for enrollment in enrollments:
        course = enrollment.course
        
        total_lessons = Lesson.objects.filter(
            module__course=course
        ).count()
        
        completed_count = LessonCompletion.objects.filter(
            user=request.user,
            lesson__module__course=course
        ).count()
        
        progress_percentage = 0
        if total_lessons > 0:
            progress_percentage = int((completed_count / total_lessons) * 100)
        
        is_completed = completed_count == total_lessons and total_lessons > 0
        
        # Get the next lesson to continue
        next_lesson = None
        if not is_completed:
            # Find the first incomplete lesson
            lessons = Lesson.objects.filter(
                module__course=course
            ).order_by("module__order", "order")
            
            completed_ids = LessonCompletion.objects.filter(
                user=request.user,
                lesson__module__course=course
            ).values_list('lesson_id', flat=True)
            
            for lesson in lessons:
                if lesson.id not in completed_ids:
                    next_lesson = lesson
                    break
        
        course_info = {
            "course": course,
            "total_lessons": total_lessons,
            "completed_count": completed_count,
            "progress_percentage": progress_percentage,
            "completed": is_completed,
            "next_lesson": next_lesson,
            "enrolled_at": enrollment.enrolled_at,
        }
        
        course_data.append(course_info)
        
        # Separate into in-progress and completed
        if is_completed:
            completed_courses.append(course_info)
        else:
            in_progress_courses.append(course_info)
    
    # Sort in-progress courses by enrollment date (most recent first)
    in_progress_courses.sort(key=lambda x: x['enrolled_at'], reverse=True)
    
    # Get payment history
    payment_history = Payment.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get recent activity (last 5 completed lessons)
    recent_activity = LessonCompletion.objects.filter(
        user=request.user
    ).select_related('lesson', 'lesson__module__course').order_by('-completed_at')[:5]
    
    return render(request, "courses/dashboard.html", {
        "total_xp": total_xp,
        "level_number": level_number,
        "level_title": level_title,
        "level_progress_percent": level_progress_percent,
        "next_level_title": next_level_title,
        "all_achievements": all_achievements,
        "unlocked_ids": unlocked_ids,
        "course_data": course_data,
        "in_progress_courses": in_progress_courses,
        "completed_courses": completed_courses,
        "payment_history": payment_history,
        "recommendations": recommendations,
        "achievement_progress": achievement_progress,
        "recent_achievements": recent_achievements,
        "recent_activity": recent_activity,
    })

@login_required
def resume_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # must be enrolled
    is_enrolled = course.enrollments.filter(user=request.user).exists()
    if not is_enrolled:
        return render(request, "courses/not_enrolled.html", {"course": course})

    lessons = Lesson.objects.filter(
        module__course=course
    ).order_by("module__order", "order")

    completed_ids = set(
        LessonCompletion.objects.filter(
            user=request.user,
            lesson__module__course=course
        ).values_list("lesson_id", flat=True)
    )

    for lesson in lessons:
        if lesson.id not in completed_ids:
            return redirect("lesson_detail", lesson_id=lesson.id)

    # if all completed → go to last lesson
    if lessons.exists():
        return redirect("lesson_detail", lesson_id=lessons.last().id)

    return redirect("dashboard")


@login_required
def course_completed(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Security check - must be enrolled
    is_enrolled = course.enrollments.filter(user=request.user).exists()
    if not is_enrolled:
        return render(request, "courses/not_enrolled.html", {"course": course})
    
    # Calculate total lessons and completed lessons
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = LessonCompletion.objects.filter(
        user=request.user,
        lesson__module__course=course
    ).count()
    
    # Calculate XP earned for this course (10 XP per lesson)
    course_xp = completed_lessons * 10
    
    # Check if user already has a certificate for this course
    from .models import Certificate
    has_certificate = Certificate.objects.filter(user=request.user, course=course).exists()

    return render(request, "courses/course_completed.html", {
        "course": course,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "course_xp": course_xp,
        "has_certificate": has_certificate,
    })

@login_required
def course_checkout(request, course_id):
    """
    Display checkout page for a paid course.
    """
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, f"You are already enrolled in '{course.title}'.")
        return redirect('course_detail', course_id=course.id)
    
    # Check if course is actually paid
    if course.is_free():
        messages.info(request, f"'{course.title}' is free. Redirecting to enrollment...")
        return redirect('enroll_course', course_id=course.id)
    
    return render(request, 'courses/course_checkout.html', {
        'course': course,
        'stripe_public_key': setting.STRIPE_PUBLISHABLE_KEY,
    })

# @login_required
# def process_payment(request, course_id):
#     """
#     Process payment for a course (simulated for now).
#     """
#     if request.method != 'POST':
#         return redirect('course_checkout', course_id=course_id)
    
#     course = get_object_or_404(Course, id=course_id, is_published=True)
    
#     # Check if already enrolled
#     if Enrollment.objects.filter(user=request.user, course=course).exists():
#         messages.info(request, f"You are already enrolled in '{course.title}'.")
#         return redirect('course_detail', course_id=course.id)
    
#     # Check if course is free (shouldn't happen but as safety)
#     if course.is_free():
#         return redirect('enroll_course', course_id=course.id)
    
#     # Simulate payment processing
#     # In a real implementation, this would communicate with Stripe
    
#     # Create a payment record
#     payment = Payment.objects.create(
#         user=request.user,
#         course=course,
#         stripe_payment_intent_id=f"simulated_{int(time.time())}",
#         stripe_checkout_session_id=f"simulated_session_{int(time.time())}",
#         amount=course.price,
#         currency="USD",
#         status="succeeded"
#     )
    
#     # Enroll the user
#     enrollment, created = Enrollment.objects.get_or_create(
#         user=request.user,
#         course=course
#     )
    
#     if created:
#         # Award XP for enrollment (even paid courses get XP)
#         XPEvent.objects.create(
#             user=request.user,
#             points=25,
#             reason=f"Enrolled in paid course: {course.title}",
#         )
        
#         # Award XP for payment (bonus for supporting platform)
#         XPEvent.objects.create(
#             user=request.user,
#             points=50,
#             reason=f"Purchased course: {course.title}",
#         )
    
#     messages.success(request, f"🎉 Payment successful! You are now enrolled in '{course.title}'.")
#     return redirect('course_detail', course_id=course.id)

@login_required
def create_checkout_session(request, course_id):
    """
    Create a Stripe Checkout Session for course purchase.
    """
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, f"You are already enrolled in '{course.title}'.")
        return redirect('course_detail', course_id=course.id)
    
    # Check if course is free
    if course.is_free():
        return redirect('enroll_course', course_id=course.id)
    
    # Check for existing pending payment
    existing_payment = Payment.objects.filter(
        user=request.user,
        course=course,
        status='pending'
    ).first()
    
    if existing_payment:
        # Try to retrieve existing session
        try:
            session = stripe.checkout.Session.retrieve(existing_payment.stripe_checkout_session_id)
            return redirect(session.url)
        except:
            # Session expired or invalid, continue to create new one
            pass
    
    try:
        # Build URLs
        success_url = request.build_absolute_uri(
            reverse('payment_success', kwargs={'course_id': course.id})
        )
        cancel_url = request.build_absolute_uri(
            reverse('course_detail', kwargs={'course_id': course.id})
        )
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': course.title,
                        'description': course.description[:500] if course.description else "",
                    },
                    'unit_amount': int(course.price * 100),  # Convert to cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
            metadata={
                'course_id': str(course.id),
                'user_id': str(request.user.id),
            },
            customer_email=request.user.email,
        )
        
        # Generate unique payment intent ID
        payment_intent_id = checkout_session.payment_intent or f"pending_{checkout_session.id}"
        
        # Create a pending payment record
        Payment.objects.create(
            user=request.user,
            course=course,
            stripe_payment_intent_id=payment_intent_id,
            stripe_checkout_session_id=checkout_session.id,
            amount=course.price,
            currency="USD",
            status="pending"
        )
        
        # Redirect to Stripe Checkout
        return redirect(checkout_session.url)
        
    except Exception as e:
        messages.error(request, f"Payment error: {str(e)}")
        return redirect('course_checkout', course_id=course.id)
    
@login_required
def payment_success(request, course_id):
    """
    Handle successful payment and enroll user.
    """
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, "Invalid payment session.")
        return redirect('course_detail', course_id=course_id)
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify the session belongs to this user/course
        if str(session.metadata.get('user_id')) != str(request.user.id):
            messages.error(request, "This payment session doesn't belong to you.")
            return redirect('course_detail', course_id=course_id)
        
        if str(session.metadata.get('course_id')) != str(course_id):
            messages.error(request, "Payment session course mismatch.")
            return redirect('course_detail', course_id=course_id)
        
        course = get_object_or_404(Course, id=course_id)
        
        # Find or create payment record
        payment, created = Payment.objects.get_or_create(
            stripe_checkout_session_id=session_id,
            defaults={
                'user': request.user,
                'course': course,
                'stripe_payment_intent_id': session.payment_intent or '',
                'amount': course.price,
                'currency': 'USD',
                'status': 'pending'
            }
        )
        
        # Update payment status
        if session.payment_status == 'paid':
            payment.status = 'succeeded'
            payment.stripe_payment_intent_id = session.payment_intent or payment.stripe_payment_intent_id
            payment.save()
            
            # Enroll the user if not already
            enrollment, enrolled = Enrollment.objects.get_or_create(
                user=request.user,
                course=course
            )
            
            if enrolled:
                # Award XP
                XPEvent.objects.create(
                    user=request.user,
                    points=25,
                    reason=f"Enrolled in paid course: {course.title}",
                )
                XPEvent.objects.create(
                    user=request.user,
                    points=50,
                    reason=f"Purchased course: {course.title}",
                )
                
                # Try to send receipt email (optional)
                try:
                    payment.send_receipt_email()
                except Exception as email_error:
                    # Don't crash the payment flow if email fails
                    print(f"Receipt email failed (non-critical): {email_error}")
                    # You could log this to a proper logging system
            
            messages.success(request, f"🎉 Payment successful! You are now enrolled in '{course.title}'.")
        else:
            payment.status = 'pending'
            payment.save()
            messages.warning(request, "Payment is still processing. Please wait a moment.")
        
        return redirect('course_detail', course_id=course_id)
        
    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error: {str(e)}")
        return redirect('course_detail', course_id=course_id)
    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect('course_detail', course_id=course_id)

@login_required
def payment_receipt(request, payment_id):
    """
    Display payment receipt/invoice.
    """
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Verify user owns this payment
    if payment.user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('dashboard')
    
    receipt_data = payment.get_receipt_data()
    
    return render(request, 'courses/payment_receipt.html', {
        'payment': payment,
        'receipt': receipt_data,
    })

def leaderboard(request):
    """
    Display user leaderboard based on XP.
    """
    from django.db.models import Sum
    
    # Get users with their XP totals using aggregation (more efficient)
    users_with_xp = User.objects.annotate(
        total_xp=Sum('xp_events__points')
    ).filter(total_xp__gt=0).order_by('-total_xp')[:50]
    
    # Prepare data for template
    leaderboard_data = []
    for i, user in enumerate(users_with_xp, 1):
        total_xp = user.total_xp or 0
        current_level, _ = get_level_progress(total_xp)
        
        leaderboard_data.append({
            'user': user,
            'total_xp': total_xp,
            'level_number': current_level[0],
            'level_title': current_level[1],
            'achievement_count': UserAchievement.objects.filter(user=user).count(),
            'rank': i,
        })
    
    # Get current user's position and XP
    current_user_rank = None
    current_user_xp = 0
    
    if request.user.is_authenticated:
        current_user_xp = XPEvent.objects.filter(user=request.user).aggregate(
            Sum("points")
        )["points__sum"] or 0
        
        # Find user's rank
        for i, user in enumerate(users_with_xp, 1):
            if user.id == request.user.id:
                current_user_rank = i
                break
    
    return render(request, 'courses/leaderboard.html', {
        'leaderboard': leaderboard_data,
        'current_user_rank': current_user_rank,
        'current_user_xp': current_user_xp,
        'total_users': users_with_xp.count(),
    })

def welcome(request):
    """Welcome/landing page for the platform."""
    # Get some stats for the homepage
    total_courses = Course.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    
    # Get featured courses
    featured_courses = Course.objects.filter(is_published=True)[:3]
    
    return render(request, 'courses/welcome.html', {
        'total_courses': total_courses,
        'total_users': total_users,
        'featured_courses': featured_courses,
    })


@login_required
def add_comment(request, lesson_id):
    """
    Add a comment to a lesson or reply to another comment.
    Optimized for performance.
    """
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.lesson = lesson
            comment.user = request.user
            
            # Check if this is a reply
            parent_id = request.POST.get('parent_id')
            if parent_id and parent_id.strip() and parent_id != 'None':
                try:
                    # Use select_related to fetch the user in one query
                    parent = Comment.objects.select_related('user').get(id=parent_id)
                    comment.parent = parent
                    
                    # Send notification in background using Celery or async task
                    # For now, let's do it in a non-blocking way
                    if parent.user != request.user:
                        from .utils import send_comment_notification_async
                        # Use a thread to send email without blocking
                        import threading
                        email_thread = threading.Thread(
                            target=send_comment_notification_async,
                            args=(parent, comment, request.user)
                        )
                        email_thread.daemon = True
                        email_thread.start()
                        
                except Comment.DoesNotExist:
                    pass
            
            # Save the comment
            comment.save()
            
            # Award XP - do this in a separate operation
            XPEvent.objects.create(
                user=request.user,
                points=2,
                reason=f"Posted a comment on lesson: {lesson.title[:50]}"
            )
            
            # For AJAX requests - return minimal data
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.template.loader import render_to_string
                
                # Pre-fetch related data to avoid N+1 queries in template
                comment = Comment.objects.select_related(
                    'user', 'parent'
                ).prefetch_related(
                    'upvotes', 'replies'
                ).get(id=comment.id)
                
                # Render only what's needed
                html = render_to_string('courses/comment_partial.html', {
                    'comment': comment,
                    'user': request.user,
                }, request=request)
                
                return JsonResponse({
                    'status': 'success',
                    'html': html,
                    'comment_id': comment.id,
                    'message': 'Comment posted successfully!'
                })
            else:
                messages.success(request, "Your comment has been posted!")
                return redirect('lesson_detail', lesson_id=lesson.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                }, status=400)
    
    return redirect('lesson_detail', lesson_id=lesson.id)

@login_required
@require_POST
@ensure_csrf_cookie
def upvote_comment(request, comment_id):
    """
    Toggle upvote on a comment.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    if comment.user == request.user:
        return JsonResponse({
            'status': 'error',
            'message': 'You cannot upvote your own comment'
        }, status=400)
    
    if comment.upvotes.filter(id=request.user.id).exists():
        # Remove upvote
        comment.upvotes.remove(request.user)
        action = 'removed'
    else:
        # Add upvote
        comment.upvotes.add(request.user)
        action = 'added'
        
        # Award XP to comment author (small bonus for getting upvotes)
        if comment.user != request.user:
            # Check if this is the first upvote on this comment
            if comment.upvotes.count() == 1:
                XPEvent.objects.create(
                    user=comment.user,
                    points=1,
                    reason=f"Your comment received an upvote"
                )
    
    return JsonResponse({
        'status': 'success',
        'action': action,
        'total_upvotes': comment.upvotes.count(),
        'user_upvoted': comment.upvotes.filter(id=request.user.id).exists()
    })

@login_required
def edit_comment(request, comment_id):
    """
    Edit a comment.
    """
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.is_edited = True
            comment.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'content': comment.content
                })
            
            messages.success(request, "Your comment has been updated!")
            return redirect('lesson_detail', lesson_id=comment.lesson.id)
    else:
        form = CommentForm(instance=comment)
    
    return render(request, 'courses/edit_comment.html', {
        'form': form,
        'comment': comment
    })

@login_required
def delete_comment(request, comment_id):
    """
    Delete a comment.
    """
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    lesson_id = comment.lesson.id
    
    if request.method == 'POST':
        comment.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Comment deleted successfully'
            })
        
        messages.success(request, "Your comment has been deleted.")
    
    return redirect('lesson_detail', lesson_id=lesson_id)

@login_required
def load_more_comments(request, lesson_id):
    """
    AJAX endpoint to load more comments for a lesson.
    """
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Get page number from request
    page = request.GET.get('page', 1)
    
    # Get comments with optimized queries
    comments_list = lesson.comments.filter(parent=None).select_related(
        'user'
    ).prefetch_related(
        'replies__user',
        'replies__upvotes'
    ).order_by('-created_at')
    
    paginator = Paginator(comments_list, 5)  # Match the per_page setting
    
    try:
        comments_page = paginator.page(page)
    except EmptyPage:
        return JsonResponse({
            'status': 'error',
            'message': 'No more comments'
        }, status=404)
    
    # Check upvotes for this batch
    comment_ids = [c.id for c in comments_page]
    user_upvoted = set()
    if request.user.is_authenticated:
        user_upvoted = set(Comment.upvotes.through.objects.filter(
            comment_id__in=comment_ids,
            user_id=request.user.id
        ).values_list('comment_id', flat=True))
    
    # Render each comment to HTML
    from django.template.loader import render_to_string
    comments_html = []
    for comment in comments_page:
        # Pass user_upvoted_comment_ids to the template via context
        html = render_to_string('courses/comment_partial.html', {
            'comment': comment,
            'user': request.user,
            'user_upvoted_comment_ids': user_upvoted,
        }, request=request)
        comments_html.append(html)
    
    return JsonResponse({
        'status': 'success',
        'comments': comments_html,
        'has_next': comments_page.has_next(),
        'next_page': comments_page.next_page_number() if comments_page.has_next() else None,
        'current_page': comments_page.number,
        'total_pages': paginator.num_pages,
        'total_comments': paginator.count,
    })

@login_required
def add_review(request, course_id):
    """
    Add or update a review for a course.
    """
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if user is enrolled
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, "You must be enrolled in this course to review it.")
        return redirect('course_detail', course_id=course.id)
    
    # Check if user already reviewed
    existing_review = Review.objects.filter(course=course, user=request.user).first()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.save()
            
            messages.success(request, "Thank you for your review!")
            
            # Award XP for reviewing (small bonus)
            if not existing_review:  # Only for new reviews, not edits
                XPEvent.objects.create(
                    user=request.user,
                    points=5,
                    reason=f"Reviewed course: {course.title[:50]}"
                )
            
            return redirect('course_detail', course_id=course.id)
    else:
        form = ReviewForm(instance=existing_review)
    
    return render(request, 'courses/review_form.html', {
        'course': course,
        'form': form,
        'is_editing': existing_review is not None,
        'review': existing_review,  # Add this line to pass the review to template
    })

@login_required
@require_POST
@ensure_csrf_cookie
def helpful_review(request, review_id):
    """
    Toggle helpful vote on a review.
    """
    review = get_object_or_404(Review, id=review_id)
    
    # Add debug prints
    print(f"Review user ID: {review.user.id}, Request user ID: {request.user.id}")
    print(f"Review user email: {review.user.email}, Request user email: {request.user.email}")
    
    if review.user == request.user:
        print("User tried to vote on their own review")
        return JsonResponse({
            'status': 'error',
            'message': 'You cannot vote on your own review'
        }, status=400)
    
    if review.helpful_votes.filter(id=request.user.id).exists():
        # Remove vote
        review.helpful_votes.remove(request.user)
        action = 'removed'
        print("Vote removed")
    else:
        # Add vote
        review.helpful_votes.add(request.user)
        action = 'added'
        print("Vote added")
        
        # Award XP to reviewer (small bonus for getting helpful votes)
        if review.helpful_votes.count() == 5:  # Milestone: 5 helpful votes
            XPEvent.objects.create(
                user=review.user,
                points=10,
                reason=f"Your review for {review.course.title[:30]} is helping others!"
            )
    
    return JsonResponse({
        'status': 'success',
        'action': action,
        'total_helpful': review.helpful_votes.count(),
        'user_helpful': review.helpful_votes.filter(id=request.user.id).exists()
    })

@login_required
def delete_review(request, review_id):
    """
    Delete a review.
    """
    review = get_object_or_404(Review, id=review_id, user=request.user)
    course_id = review.course.id
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, "Your review has been deleted.")
    
    return redirect('course_detail', course_id=course_id)


@login_required
def generate_certificate(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user completed the course
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = LessonCompletion.objects.filter(
        user=request.user,
        lesson__module__course=course
    ).count()
    
    if completed_lessons < total_lessons:
        messages.error(request, "You must complete all lessons to get a certificate.")
        return redirect('course_detail', course_id=course.id)
    
    # Get or create certificate
    certificate, created = Certificate.objects.get_or_create(
        user=request.user,
        course=course
    )
    
    # Increment download count
    certificate.download_count += 1
    certificate.save()
    
    # Render HTML
    html_string = render_to_string('courses/certificate.html', {
        'user': request.user,
        'course': course,
        'certificate': certificate
    })
    
    # Generate PDF
    html = HTML(string=html_string)
    
    # Create HTTP response with PDF - FIXED LINE BELOW
    # Use course.id as fallback if slug doesn't exist
    slug_value = course.slug if hasattr(course, 'slug') and course.slug else f"course-{course.id}"
    filename = f"certificate_{slug_value}_{request.user.id}.pdf"
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Write PDF to response
    html.write_pdf(response)
    
    return response