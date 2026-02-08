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

    return redirect("lesson_detail", lesson_id=lesson.id)
