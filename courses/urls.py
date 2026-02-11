from django.urls import path
from . import views



urlpatterns = [
    path("", views.welcome, name="welcome"),  # Homepage at /
    path("dashboard/", views.dashboard, name="dashboard"),
    path("courses/", views.course_list, name="course_list"),  # Course list at /courses/
    path("courses/<int:course_id>/", views.course_detail, name="course_detail"),
    path("courses/<int:course_id>/enroll/", views.enroll_course, name="enroll_course"),
    path("courses/<int:course_id>/checkout/", views.course_checkout, name="course_checkout"),
    path("courses/<int:course_id>/create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
    path("courses/<int:course_id>/payment-success/", views.payment_success, name="payment_success"),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:lesson_id>/complete/", views.mark_lesson_complete, name="mark_lesson_complete"),
    path("courses/<int:course_id>/resume/", views.resume_course, name="resume_course"),
    path("courses/<int:course_id>/completed/", views.course_completed, name="course_completed"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("payments/<int:payment_id>/receipt/", views.payment_receipt, name="payment_receipt"),
]