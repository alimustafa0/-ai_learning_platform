from django.urls import path
from . import views


urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("<int:course_id>/", views.course_detail, name="course_detail"),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:lesson_id>/complete/", views.mark_lesson_complete, name="mark_lesson_complete"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
