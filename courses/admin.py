from django.contrib import admin
from .models import Course, Module, Lesson


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
