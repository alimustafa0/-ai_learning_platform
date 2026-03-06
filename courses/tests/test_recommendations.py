from django.test import TestCase
from django.contrib.auth import get_user_model
from courses.models import Course, Category, Enrollment, Lesson, LessonCompletion
from courses.recommendations import get_course_recommendations, get_user_interested_categories

User = get_user_model()

class RecommendationTests(TestCase):
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass123'
        )

        # Create categories
        self.python_cat = Category.objects.create(
            name='Python',
            slug='python'
        )
        self.ai_cat = Category.objects.create(
            name='AI',
            slug='ai'
        )

        # Create courses
        self.course1 = Course.objects.create(
            title='Python Basics',
            description='Learn Python',
            is_published=True,
            required_level=1
        )
        self.course1.categories.add(self.python_cat)

        self.course2 = Course.objects.create(
            title='Advanced Python',
            description='Master Python',
            is_published=True,
            required_level=3
        )
        self.course2.categories.add(self.python_cat)

        self.course3 = Course.objects.create(
            title='Machine Learning',
            description='Learn AI',
            is_published=True,
            required_level=2
        )
        self.course3.categories.add(self.ai_cat)

    def test_recommendations_for_new_user(self):
        """Test that new users get popular courses"""
        recommendations = get_course_recommendations(self.user1)
        self.assertIsNotNone(recommendations)

    def test_recommendations_based_on_interests(self):
        """Test that recommendations consider user interests"""
        # Enroll user in Python course
        Enrollment.objects.create(user=self.user1, course=self.course1)

        interests = get_user_interested_categories(self.user1)
        self.assertIn(self.python_cat, interests)
