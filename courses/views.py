from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, LessonCompletion
import markdown


def course_list(request):
    courses = Course.objects.filter(is_published=True)
    return render(request, "courses/course_list.html", {"courses": courses})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_published=True)
    return render(request, "courses/course_detail.html", {"course": course})


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    html_content = markdown.markdown(lesson.content)

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

    progress_percentage = 0
    if total_lessons > 0:
        progress_percentage = int((completed_count / total_lessons) * 100)

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
        },
    )

@login_required
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    # security gate again
    is_enrolled = course.enrollments.filter(user=request.user).exists()
    if not is_enrolled:
        return render(request, "courses/not_enrolled.html", {"course": course})

    # create completion if not exists
    LessonCompletion.objects.get_or_create(
        user=request.user,
        lesson=lesson,
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
    enrollments = request.user.enrollments.select_related("course")

    data = []

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

        data.append({
            "course": course,
            "total_lessons": total_lessons,
            "completed_count": completed_count,
            "progress_percentage": progress_percentage,
            "completed": is_completed,
        })

    return render(request, "courses/dashboard.html", {"data": data})

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
