from django.contrib import admin
from . import models
from .models import Course, Module, Lesson, Enrollment, LessonCompletion, XPEvent, Achievement, UserAchievement, Category, Comment, Payment, Refund
from ckeditor.widgets import CKEditorWidget


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ("order",)
    formfield_overrides = {  # <-- ADD this
        models.RichTextField: {'widget': CKEditorWidget},
    }


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
    list_display = ("title", "is_published", "price", "created_at", "required_level")
    list_filter = ("is_published", "categories", "price")
    search_fields = ("title", "categories__name")
    filter_horizontal = ("categories",)
    inlines = [ModuleInline]
    # Fields to show in the edit form
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'is_published')
        }),
        ('Pricing', {
            'fields': ('price', 'stripe_price_id', 'stripe_product_id'),
            'classes': ('collapse',),
        }),
        ('Requirements', {
            'fields': ('required_level', 'categories')
        }),
    )

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

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'course')
    search_fields = ('user__email', 'course__title', 'stripe_payment_intent_id')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    actions = ['refund_payments']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'course', 'amount', 'currency', 'status')
        }),
        ('Stripe IDs', {
            'fields': ('stripe_payment_intent_id', 'stripe_checkout_session_id'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def refund_payments(self, request, queryset):
        """
        Admin action to refund selected payments.
        """
        # Only allow refunding succeeded payments
        queryset = queryset.filter(status='succeeded')
        
        refunded_count = 0
        failed_count = 0
        
        for payment in queryset:
            # Calculate refundable amount (full amount for now)
            refundable = payment.amount
            
            # Check if already refunded
            total_refunded = sum(refund.amount for refund in payment.refunds.filter(status='succeeded'))
            if total_refunded >= payment.amount:
                self.message_user(request, f"Payment {payment.id} already fully refunded.", level='warning')
                continue
            
            if total_refunded > 0:
                refundable = payment.amount - total_refunded
            
            try:
                refund, created, stripe_refund = payment.create_refund(
                    amount=refundable,
                    reason="Admin refund via dashboard",
                    admin_user=request.user
                )
                
                if created and stripe_refund:
                    refunded_count += 1
                    self.message_user(request, f"Refunded ${refundable} for payment {payment.id}. Refund ID: {stripe_refund.id}")
                else:
                    failed_count += 1
                    self.message_user(request, f"Failed to refund payment {payment.id}", level='error')
                    
            except Exception as e:
                failed_count += 1
                self.message_user(request, f"Error refunding payment {payment.id}: {str(e)}", level='error')
        
        self.message_user(request, f"Successfully refunded {refunded_count} payment(s). {failed_count} failed.")
    
    refund_payments.short_description = "Refund selected payments"

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('payment', 'amount', 'status', 'admin_user', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__stripe_payment_intent_id', 'reason', 'admin_user__email')
    readonly_fields = ('created_at', 'updated_at', 'stripe_refund_id')
    
    fieldsets = (
        (None, {
            'fields': ('payment', 'amount', 'reason', 'status')
        }),
        ('Stripe', {
            'fields': ('stripe_refund_id',),
            'classes': ('collapse',),
        }),
        ('Admin', {
            'fields': ('admin_user',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )