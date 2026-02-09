from django.contrib import admin
from .models import Course, Module, Lesson, Enrollment, LessonCompletion, XPEvent, Achievement, UserAchievement, Category, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


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
    list_display = ("title", "is_published", "created_at", "required_level")
    list_filter = ("is_published", "categories")
    search_fields = ("title", "categories__name")
    filter_horizontal = ("categories",)
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

admin.site.register(Achievement)
admin.site.register(UserAchievement)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'truncated_content', 'created_at', 'is_edited', 'is_reply_display')
    list_filter = ('created_at', 'is_edited', 'lesson')
    search_fields = ('content', 'user__email', 'lesson__title')
    readonly_fields = ('created_at', 'updated_at')
    
    def truncated_content(self, obj):
        """Display first 50 chars of comment content."""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    truncated_content.short_description = 'Content'
    
    def is_reply_display(self, obj):
        """Display ✓ if comment is a reply."""
        return "✓" if obj.parent else ""
    is_reply_display.short_description = 'Is Reply'