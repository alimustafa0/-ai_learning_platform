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
            {
                'code': 'first-course',
                'name': 'Course Graduate',
                'description': 'Complete your first course',
                'xp_reward': 100,
                'icon': '🎓',
                'category': 'courses',
                'threshold': 1,
            },
            {
                'code': 'third-course',
                'name': 'Trifecta',
                'description': 'Complete 3 courses',
                'xp_reward': 200,
                'icon': '🏆',
                'category': 'courses',
                'threshold': 3,
            },
            {
                'code': 'fifth-course',
                'name': 'Course Collector',
                'description': 'Complete 5 courses',
                'xp_reward': 350,
                'icon': '📚',
                'category': 'courses',
                'threshold': 5,
            },
            {
                'code': 'tenth-course',
                'name': 'Knowledge Seeker',
                'description': 'Complete 10 courses',
                'xp_reward': 500,
                'icon': '🌟',
                'category': 'courses',
                'threshold': 10,
            },
            {
                'code': 'three-day-streak',
                'name': 'Getting Consistent',
                'description': 'Maintain a 3-day learning streak',
                'xp_reward': 30,
                'icon': '🔥',
                'category': 'streak',
                'threshold': 3,
            },
            {
                'code': 'week-streak',
                'name': 'Week Warrior',
                'description': 'Maintain a 7-day learning streak',
                'xp_reward': 70,
                'icon': '⚡',
                'category': 'streak',
                'threshold': 7,
            },
            {
                'code': 'two-week-streak',
                'name': 'Two-Week Dedication',
                'description': 'Maintain a 14-day learning streak',
                'xp_reward': 150,
                'icon': '🌟',
                'category': 'streak',
                'threshold': 14,
            },
            {
                'code': 'month-streak',
                'name': 'Monthly Master',
                'description': 'Maintain a 30-day learning streak',
                'xp_reward': 300,
                'icon': '👑',
                'category': 'streak',
                'threshold': 30,
            },
            {
                'code': 'two-month-streak',
                'name': 'Two-Month Champion',
                'description': 'Maintain a 60-day learning streak',
                'xp_reward': 500,
                'icon': '🏆',
                'category': 'streak',
                'threshold': 60,
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
