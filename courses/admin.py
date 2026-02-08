from django.contrib import admin
from .models import Course, Module, Lesson, Enrollment, LessonCompletion, XPEvent


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ("order",)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    ordering = ("course", "order")
    inlines = [LessonInline]


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    ordering = ("order",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title",)
    inlines = [ModuleInline]

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at")
    list_filter = ("course",)
    search_fields = ("user__email",)

@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "completed_at")
    list_filter = ("lesson",)
    search_fields = ("user__email",)

@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("user__email",)
