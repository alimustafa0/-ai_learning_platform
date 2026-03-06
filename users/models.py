from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not password:
            raise ValueError("Users must have a password")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    # === PROFILE FIELDS ===
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Biography",
        help_text="Tell us about yourself (max 500 characters)"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Profile Picture"
    )
    website = models.URLField(
        blank=True,
        verbose_name="Personal Website",
        help_text="Optional: Your blog, portfolio, or social media link"
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Location",
        help_text="City, Country"
    )
    # ======================

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()


    class Meta:
        ordering = ['email', 'first_name', 'last_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['date_joined']),
        ]

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """
        Return the short name for the user (first name).
        """
        return self.first_name

    def __str__(self):
        """
        Return a string representation of the user.
        Shows email and name if available.
        """
        if self.first_name or self.last_name:
            return f"{self.email} ({self.get_full_name()})"
        return self.email

class Follow(models.Model):
    """
    Tracks user follows (many-to-many self-referential).
    """
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.follower.email} follows {self.following.email}"
