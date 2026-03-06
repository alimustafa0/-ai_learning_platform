from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import (
    Course, Module, Lesson, Enrollment, LessonCompletion,
    XPEvent, Achievement, UserAchievement, Payment
)
from users.models import User
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Student'
        )
        self.client.login(email='student@example.com', password='testpass123')

        # Create courses
        self.course1 = Course.objects.create(
            title="Course 1",
            description="First course",
            is_published=True,
            required_level=0,
            price=0
        )

        self.course2 = Course.objects.create(
            title="Course 2",
            description="Second course",
            is_published=True,
            required_level=0,
            price=49.99
        )

        # Create modules and lessons for course1
        self.module1 = Module.objects.create(
            course=self.course1,
            title="Module 1",
            order=1
        )

        self.lesson1 = Lesson.objects.create(
            module=self.module1,
            title="Lesson 1",
            content="Content 1",
            order=1
        )

        self.lesson2 = Lesson.objects.create(
            module=self.module1,
            title="Lesson 2",
            content="Content 2",
            order=2
        )

        # Create modules and lessons for course2
        self.module2 = Module.objects.create(
            course=self.course2,
            title="Module 1",
            order=1
        )

        self.lesson3 = Lesson.objects.create(
            module=self.module2,
            title="Lesson 1",
            content="Content 1",
            order=1
        )

        # Enroll user in courses
        self.enrollment1 = Enrollment.objects.create(
            user=self.user,
            course=self.course1,
            enrolled_at=timezone.now() - timedelta(days=5)
        )

        self.enrollment2 = Enrollment.objects.create(
            user=self.user,
            course=self.course2,
            enrolled_at=timezone.now() - timedelta(days=2)
        )

        # Add XP for level testing
        XPEvent.objects.create(user=self.user, points=150, reason="Test XP")

        # Create achievements
        self.achievement1 = Achievement.objects.create(
            name="First Lesson",
            description="Complete your first lesson",
            code="first-lesson",
            xp_reward=50
        )

        self.achievement2 = Achievement.objects.create(
            name="Course Master",
            description="Complete a course",
            code="course-master",
            xp_reward=100
        )

    def test_dashboard_requires_login(self):
        """Test that dashboard redirects anonymous users"""
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_dashboard_loads_successfully(self):
        """Test that dashboard loads for logged in user"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/dashboard.html')

    def test_dashboard_shows_user_stats(self):
        """Test that user XP and level are displayed"""
        response = self.client.get(reverse('dashboard'))

        # Check XP
        self.assertEqual(response.context['total_xp'], 150)

        # Check level (150 XP should be level 2 based on your level system)
        self.assertIn('level_number', response.context)
        self.assertIn('level_title', response.context)
        self.assertIn('level_progress_percent', response.context)

    def test_dashboard_shows_enrolled_courses(self):
        """Test that enrolled courses are shown"""
        response = self.client.get(reverse('dashboard'))

        # Should have 2 courses total
        self.assertEqual(len(response.context['course_data']), 2)

        # In-progress courses (none completed yet)
        self.assertEqual(len(response.context['in_progress_courses']), 2)
        self.assertEqual(len(response.context['completed_courses']), 0)

        # Check course1 data
        course1_info = None
        for info in response.context['in_progress_courses']:
            if info['course'].id == self.course1.id:
                course1_info = info
                break

        self.assertIsNotNone(course1_info)
        self.assertEqual(course1_info['total_lessons'], 2)
        self.assertEqual(course1_info['completed_count'], 0)
        self.assertEqual(course1_info['progress_percentage'], 0)
        self.assertFalse(course1_info['completed'])
        self.assertEqual(course1_info['next_lesson'], self.lesson1)

    def test_dashboard_calculates_course_progress(self):
        """Test that course progress is calculated correctly"""
        # Complete one lesson
        LessonCompletion.objects.create(
            user=self.user,
            lesson=self.lesson1
        )

        response = self.client.get(reverse('dashboard'))

        # Find course1 in the list
        course_info = None
        for info in response.context['in_progress_courses']:
            if info['course'].id == self.course1.id:
                course_info = info
                break

        self.assertIsNotNone(course_info)
        self.assertEqual(course_info['completed_count'], 1)
        self.assertEqual(course_info['progress_percentage'], 50)
        self.assertEqual(course_info['next_lesson'], self.lesson2)

    def test_dashboard_shows_completed_courses(self):
        """Test that completed courses appear in completed section"""
        # Complete all lessons for course1
        LessonCompletion.objects.create(user=self.user, lesson=self.lesson1)
        LessonCompletion.objects.create(user=self.user, lesson=self.lesson2)

        response = self.client.get(reverse('dashboard'))

        # Should have 1 completed, 1 in-progress
        self.assertEqual(len(response.context['completed_courses']), 1)
        self.assertEqual(len(response.context['in_progress_courses']), 1)

        completed_course = response.context['completed_courses'][0]
        self.assertEqual(completed_course['course'], self.course1)
        self.assertTrue(completed_course['completed'])
        self.assertEqual(completed_course['progress_percentage'], 100)

    def test_dashboard_shows_achievements(self):
        """Test that achievements are displayed"""
        # Unlock one achievement
        UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement1
        )

        response = self.client.get(reverse('dashboard'))

        # Check all achievements are in context
        self.assertEqual(len(response.context['all_achievements']), 2)

        # Check unlocked IDs
        unlocked_ids = list(response.context['unlocked_ids'])
        self.assertIn(self.achievement1.id, unlocked_ids)
        self.assertNotIn(self.achievement2.id, unlocked_ids)

        # Check achievement progress
        self.assertIn('achievement_progress', response.context)
        self.assertIn('recent_achievements', response.context)

    def test_dashboard_shows_recent_activity(self):
        """Test that recent lesson completions are shown"""
        # Complete lessons at different times
        now = timezone.now()

        completion1 = LessonCompletion.objects.create(
            user=self.user,
            lesson=self.lesson1
        )
        completion1.completed_at = now - timedelta(hours=2)
        completion1.save()

        completion2 = LessonCompletion.objects.create(
            user=self.user,
            lesson=self.lesson2
        )
        completion2.completed_at = now - timedelta(hours=1)
        completion2.save()

        response = self.client.get(reverse('dashboard'))

        recent = response.context['recent_activity']
        self.assertEqual(len(recent), 2)
        # Most recent first
        self.assertEqual(recent[0], completion2)
        self.assertEqual(recent[1], completion1)

    def test_dashboard_shows_payment_history(self):
        """Test that payment history is shown"""
        # Create some payments with unique session IDs
        payment1 = Payment.objects.create(
            user=self.user,
            course=self.course2,
            amount=49.99,
            currency="USD",
            status="succeeded",
            stripe_payment_intent_id="pi_1",
            stripe_checkout_session_id="cs_1_unique_value_123"  # Add unique session ID
        )
        payment1.created_at = timezone.now() - timedelta(days=1)
        payment1.save()

        payment2 = Payment.objects.create(
            user=self.user,
            course=self.course1,  # Free course, but could have payment
            amount=0,
            currency="USD",
            status="succeeded",
            stripe_payment_intent_id="pi_2",
            stripe_checkout_session_id="cs_2_unique_value_456"  # Add unique session ID
        )
        payment2.created_at = timezone.now()
        payment2.save()

        response = self.client.get(reverse('dashboard'))

        payments = response.context['payment_history']
        self.assertEqual(len(payments), 2)
        # Most recent first
        self.assertEqual(payments[0], payment2)
        self.assertEqual(payments[1], payment1)

    def test_dashboard_shows_recommendations(self):
        """Test that course recommendations are shown"""
        from courses.recommendations import get_course_recommendations

        response = self.client.get(reverse('dashboard'))

        self.assertIn('recommendations', response.context)
        # Recommendations function should return something
        self.assertIsNotNone(response.context['recommendations'])

    def test_dashboard_sorts_courses_by_enrollment_date(self):
        """Test that in-progress courses are sorted by enrollment date (newest first)"""
        response = self.client.get(reverse('dashboard'))

        in_progress = response.context['in_progress_courses']

        # Course2 enrolled more recently (2 days ago vs 5 days ago)
        self.assertEqual(in_progress[0]['course'], self.course2)
        self.assertEqual(in_progress[1]['course'], self.course1)
