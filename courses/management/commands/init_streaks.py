from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from courses.models import LearningStreak, LessonCompletion
from datetime import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize streaks for existing users based on their lesson completion history'

    def handle(self, *args, **options):
        users = User.objects.all()
        
        for user in users:
            streak, created = LearningStreak.objects.get_or_create(user=user)
            
            # Get all lesson completions for this user
            completions = LessonCompletion.objects.filter(
                user=user
            ).order_by('completed_at')
            
            if completions.exists():
                # Set last activity to most recent completion
                streak.last_activity_date = completions.last().completed_at.date()
                
                # Calculate current streak (simplified)
                # For a more accurate calculation, you'd need to check consecutive days
                streak.current_streak = 1
                streak.longest_streak = 1
                
                streak.save()
                self.stdout.write(self.style.SUCCESS(f"Initialized streak for {user.email}"))
            else:
                self.stdout.write(f"No completions for {user.email}")