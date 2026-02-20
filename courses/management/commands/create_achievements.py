# courses/management/commands/create_achievements.py
from django.core.management.base import BaseCommand
from courses.models import Achievement

class Command(BaseCommand):
    help = 'Create all achievements for the platform'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating achievements...')
        
        # Lesson completion achievements
        achievements = [
            {
                'code': 'first-lesson',
                'name': 'First Steps',
                'description': 'Complete your first lesson',
                'xp_reward': 25,
                'icon': '📚',
                'category': 'lessons',
                'threshold': 1,
            },
            # We'll add more step by step
        ]
        
        for ach_data in achievements:
            ach, created = Achievement.objects.get_or_create(
                code=ach_data['code'],
                defaults=ach_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {ach.name}"))
            else:
                self.stdout.write(f"Already exists: {ach.name}")
        
        self.stdout.write(self.style.SUCCESS('Done!'))