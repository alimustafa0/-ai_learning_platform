from django.db import models
from django.conf import settings
from ckeditor.fields import RichTextField


class Category(models.Model):
    """
    Course categories/tags for organization (e.g., Python, AI, Web Development).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly version of the name")
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    required_level = models.IntegerField(default=1)

    categories = models.ManyToManyField(Category, blank=True, related_name="courses")

    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Price in USD. 0.00 = free course"
    )

    stripe_price_id = models.CharField(max_length=100, blank=True, help_text="Stripe Price ID for this course")
    stripe_product_id = models.CharField(max_length=100, blank=True, help_text="Stripe Product ID for this course")

    def __str__(self):
        return self.title
    
    def is_free(self):
        return self.price == 0


class Module(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.order}. {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    title = models.CharField(max_length=255)
    # content = models.TextField(help_text="Markdown-supported lesson content")     # old field
    content = RichTextField(help_text="Rich text lesson content")
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField()
    is_free_preview = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("module", "order")

    def __str__(self):
        return f"{self.order}. {self.title}"

from django.conf import settings


class Enrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user.email} enrolled in {self.course.title}"

class LessonCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="completed_lessons",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.email} completed {self.lesson.title}"

class XPEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_events",
    )
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} +{self.points} XP for {self.reason}"

    
class Achievement(models.Model):
    name = models.CharField(max_length=255)
    code = models.SlugField(
        max_length=50, 
        unique=True,
        help_text="Unique identifier for use in code (e.g., 'first_lesson', 'course_complete')"
    )
    description = models.TextField(blank=True)
    xp_reward = models.IntegerField(default=50, help_text="XP awarded when earning this achievement")
    icon = models.CharField(max_length=100, blank=True, default="🏆", help_text="Emoji or icon name")
    category = models.CharField(
        max_length=50,
        choices=[
            ('lessons', 'Lessons Completed'),
            ('courses', 'Courses Completed'),
            ('xp', 'Total XP'),
            ('streak', 'Learning Streak'),
            ('special', 'Special Achievements'),
        ],
        default='special',
        help_text="Category of achievement for progress tracking"
    )
    threshold = models.IntegerField(
        default=0,
        help_text="Number required to unlock (e.g., 5 lessons, 100 XP)"
    )
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['category', 'threshold']

class UserAchievement(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement")

    def __str__(self):
        return f"{self.user.email} - {self.achievement.name}"
    

class Payment(models.Model):
    """
    Track course purchases.
    """

    def create_refund(self, amount, reason, admin_user=None):
        """
        Create a refund for this payment.
        Returns (refund, created, stripe_refund)
        """
        import stripe
        from django.conf import settings
        
        # Validate amount
        if amount <= 0:
            raise ValueError("Refund amount must be positive")
        
        if amount > self.amount:
            amount = self.amount
        
        # Check if already refunded (total refunds)
        total_refunded = sum(refund.amount for refund in self.refunds.filter(status='succeeded'))
        if total_refunded >= self.amount:
            raise ValueError("Payment already fully refunded")
        
        if total_refunded + amount > self.amount:
            amount = self.amount - total_refunded
        
        try:
            # Create refund in Stripe
            stripe_refund = stripe.Refund.create(
                payment_intent=self.stripe_payment_intent_id,
                amount=int(amount * 100),  # Convert to cents
                reason='requested_by_customer'  # or 'duplicate', 'fraudulent'
            )
            
            # Create refund record
            refund = Refund.objects.create(
                payment=self,
                admin_user=admin_user,
                stripe_refund_id=stripe_refund.id,
                amount=amount,
                reason=reason,
                status=stripe_refund.status
            )
            
            # Update payment status if fully refunded
            new_total_refunded = total_refunded + amount
            if new_total_refunded >= self.amount:
                self.status = 'refunded'
                self.save()
            
            return refund, True, stripe_refund
            
        except stripe.error.StripeError as e:
            # Create failed refund record
            refund = Refund.objects.create(
                payment=self,
                admin_user=admin_user,
                amount=amount,
                reason=f"{reason} (Failed: {str(e)})",
                status='failed'
            )
            return refund, False, None

    def generate_receipt_number(self):
        """Generate a unique receipt number."""
        return f"INV-{self.id:06d}-{self.created_at.strftime('%Y%m')}"
    
    def get_receipt_data(self):
        """Return data for receipt/invoice."""
        return {
            'receipt_number': self.generate_receipt_number(),
            'date': self.created_at.strftime('%B %d, %Y'),
            'course': self.course.title,
            'amount': f"${self.amount}",
            'user_name': self.user.get_full_name() or self.user.email,
            'user_email': self.user.email,
            'payment_method': 'Credit Card (Stripe)',
            'status': self.get_status_display(),
            'transaction_id': self.stripe_payment_intent_id,
        }
    
    def send_receipt_email(self):
        """Send receipt email to user."""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        receipt_data = self.get_receipt_data()
        
        # Get site URL, default to localhost if not set
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        # Render email content
        subject = f"Receipt for {self.course.title} - AI Learning Platform"
        message = f"""
        Thank you for your purchase!
        
        Receipt #{receipt_data['receipt_number']}
        Date: {receipt_data['date']}
        Course: {self.course.title}
        Amount: ${self.amount}
        
        You can view your receipt online at:
        {site_url}/courses/payments/{self.id}/receipt/
        
        Thank you for learning with us!
        """
        
        html_message = render_to_string('courses/email_receipt.html', {
            'payment': self,
            'receipt': receipt_data,
            'site_url': site_url,
        })
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                html_message=html_message,
            )
            return True
        except Exception as e:
            # Log error but don't crash the payment flow
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send receipt email: {e}")
            return False

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.course.title} - ${self.amount}"

class Comment(models.Model):
    """
    User comments on lessons for discussion and Q&A.
    """
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on {self.lesson.title}"
    
    def is_reply(self):
        """Check if this comment is a reply to another comment."""
        return self.parent is not None
    
class Refund(models.Model):
    """
    Track refunds for payments.
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="refunds"
    )
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="processed_refunds"
    )
    stripe_refund_id = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('canceled', 'Canceled'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund for {self.payment} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        # Ensure refund amount doesn't exceed payment amount
        if self.amount > self.payment.amount:
            self.amount = self.payment.amount
        super().save(*args, **kwargs)

