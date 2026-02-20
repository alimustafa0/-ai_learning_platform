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
            {
                'code': 'second-lesson',
                'name': 'Getting Started',
                'description': 'Complete 2 lessons',
                'xp_reward': 30,
                'icon': '📖',
                'category': 'lessons',
                'threshold': 2,
            },
            {
                'code': 'fifth-lesson',
                'name': 'Learning Streak',
                'description': 'Complete 5 lessons',
                'xp_reward': 50,
                'icon': '🔖',
                'category': 'lessons',
                'threshold': 5,
            },
            {
                'code': 'tenth-lesson',
                'name': 'Double Digits',
                'description': 'Complete 10 lessons',
                'xp_reward': 75,
                'icon': '🎯',
                'category': 'lessons',
                'threshold': 10,
            },
            {
                'code': 'twenty-fifth-lesson',
                'name': 'Dedicated Learner',
                'description': 'Complete 25 lessons',
                'xp_reward': 100,
                'icon': '⭐',
                'category': 'lessons',
                'threshold': 25,
            },
            {
                'code': 'fiftieth-lesson',
                'name': 'Half Century',
                'description': 'Complete 50 lessons',
                'xp_reward': 200,
                'icon': '🏅',
                'category': 'lessons',
                'threshold': 50,
            },
            {
                'code': 'hundredth-lesson',
                'name': 'Century Club',
                'description': 'Complete 100 lessons',
                'xp_reward': 500,
                'icon': '🏆',
                'category': 'lessons',
                'threshold': 100,
            },
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
        
        self.stdout.write(self.style.SUCCESS('Done creating lesson achievements!'))