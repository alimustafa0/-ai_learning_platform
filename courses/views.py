from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from config import settings as setting
from .models import Course, Enrollment, Lesson, LessonCompletion, XPEvent, Achievement, UserAchievement, Payment
from .forms import CommentForm
from .gamification import get_level_progress
from .achievements import check_lesson_count_achievements, check_course_completion_achievements
import time
import stripe
from django.conf import settings
from django.urls import reverse

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
    else:
        # For anonymous users, set level to 0 and not enrolled
        user_level_number = 0
        is_enrolled = False

    # Level lock check (only if required_level > 1)
    if user_level_number < course.required_level:
        return render(request, "courses/level_locked.html", {
            "course": course,
            "required_level": course.required_level,
            "user_level_number": user_level_number,
        })
    
    return render(request, "courses/course_detail.html", {
        "course": course,
        "user_level_number": user_level_number,
        "is_enrolled": is_enrolled,  # <-- NEW: pass enrollment status
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

    if completed_count == 1:
        achievement = Achievement.objects.get(name="First Lesson")

        UserAchievement.objects.get_or_create(
            user=request.user,
            achievement=achievement
        )

        messages.success(request, "🏅 Achievement Unlocked: First Lesson!")

    elif completed_count == 2:
        achievement = Achievement.objects.get(name="Second Lesson")

        UserAchievement.objects.get_or_create(
            user=request.user,
            achievement=achievement
        )

        messages.success(request, "🏅 Achievement Unlocked: Second Lesson!")

    progress_percentage = 0
    if total_lessons > 0:
        progress_percentage = int((completed_count / total_lessons) * 100)

    # === HANDLE COMMENTS ===
    comments = lesson.comments.filter(parent=None).order_by('created_at')  # Top-level comments only
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
    
    return render(
        request,
        "courses/lesson_detail.html",
        {
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
            "comments": comments,  # <-- NEW
            "comment_form": comment_form,  # <-- NEW
        },
    )

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
    # Calculate user stats FIRST (independent of enrollments)
    total_xp = XPEvent.objects.filter(user=request.user).aggregate(total=Sum('points'))['total'] or 0
    current_level, next_level = get_level_progress(total_xp)
    
    level_number, level_title, level_xp = current_level
    
    if next_level:
        next_level_number, next_level_title, next_level_xp = next_level
        xp_into_level = total_xp - level_xp
        xp_range = next_level_xp - level_xp
        level_progress_percent = int((xp_into_level / xp_range) * 100) if xp_range > 0 else 0
    else:
        # user is MAX level
        next_level_title = "MAX"
        level_progress_percent = 100
    
    # Get all achievements for display
    all_achievements = Achievement.objects.all()
    unlocked_ids = UserAchievement.objects.filter(
        user=request.user
    ).values_list("achievement_id", flat=True)
    
    # Get enrollments and course progress
    enrollments = request.user.enrollments.select_related("course")
    course_data = []
    
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
        
        course_data.append({
            "course": course,
            "total_lessons": total_lessons,
            "completed_count": completed_count,
            "progress_percentage": progress_percentage,
            "completed": is_completed,
        })

    # Get payment history
    payment_history = Payment.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(request, "courses/dashboard.html", {
        "total_xp": total_xp,
        "level_number": level_number,
        "level_title": level_title,
        "level_progress_percent": level_progress_percent,
        "next_level_title": next_level_title,
        "all_achievements": all_achievements,
        "unlocked_ids": unlocked_ids,
        "course_data": course_data,  # Renamed from 'data' for clarity
        "payment_history": payment_history,
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

    # security
    is_enrolled = course.enrollments.filter(user=request.user).exists()
    if not is_enrolled:
        return render(request, "courses/not_enrolled.html", {"course": course})

    return render(request, "courses/course_completed.html", {"course": course})

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