from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import Course, Lesson, Module, Enrollment, LessonCompletion, XPEvent
from users.models import User

User = get_user_model()

class CourseListViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        # Create test courses
        self.course1 = Course.objects.create(
            title="Test Course 1",
            description="Description 1",
            is_published=True,
            required_level=1,
            price=0  # Free course
        )

        self.course2 = Course.objects.create(
            title="Test Course 2",
            description="Description 2",
            is_published=True,
            required_level=2,
            price=49.99  # Paid course
        )

        # Unpublished course (should not appear)
        self.course3 = Course.objects.create(
            title="Unpublished Course",
            description="Should not appear",
            is_published=False,
            required_level=1
        )

    def test_welcome_view(self):
        """Test the welcome/landing page"""
        response = self.client.get(reverse('welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course 1")
        self.assertContains(response, "Test Course 2")
        self.assertNotContains(response, "Unpublished Course")
        self.assertTemplateUsed(response, 'courses/welcome.html')

    def test_course_list_view(self):
        """Test the course list page"""
        response = self.client.get(reverse('course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course 1")
        self.assertContains(response, "Test Course 2")
        self.assertNotContains(response, "Unpublished Course")
        self.assertTemplateUsed(response, 'courses/course_list.html')

    def test_course_list_shows_level_for_authenticated_user(self):
        """Test that authenticated users see their level"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_level_number', response.context)
        # User might have level 1 from XP, so we check it's an integer
        self.assertIsInstance(response.context['user_level_number'], int)


class CourseDetailViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        # Create course with modules and lessons - set required_level to 0 so it's accessible
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            is_published=True,
            required_level=0,  # Change to 0 so it's accessible to everyone
            price=0
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Test Module",
            order=1
        )

        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Test Lesson",
            content="Test Content",
            order=1
        )

    def test_course_detail_view(self):
        """Test course detail page loads"""
        response = self.client.get(reverse('course_detail', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
        self.assertContains(response, "Test Description")
        self.assertTemplateUsed(response, 'courses/course_detail.html')

    def test_course_detail_shows_login_prompt_for_anonymous(self):
        """Test anonymous users see login prompt instead of enroll button"""
        response = self.client.get(reverse('course_detail', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        # Check that login/signup links are present
        self.assertContains(response, "Login")
        self.assertContains(response, "Sign Up")
        self.assertFalse(response.context['is_enrolled'])

    def test_course_detail_shows_enroll_button_for_authenticated(self):
        """Test authenticated users see enroll button"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('course_detail', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enroll Now")
        self.assertFalse(response.context['is_enrolled'])

    def test_course_detail_shows_progress_for_enrolled_user(self):
        """Test enrolled users see their progress"""
        self.client.login(email='test@example.com', password='testpass123')

        # Enroll the user
        Enrollment.objects.create(user=self.user, course=self.course)

        response = self.client.get(reverse('course_detail', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_enrolled'])
        self.assertEqual(response.context['total_lessons'], 1)
        self.assertEqual(response.context['completed_count'], 0)
        self.assertEqual(response.context['progress_percentage'], 0)

    def test_level_locked_course(self):
        """Test course that requires higher level"""
        self.course.required_level = 5
        self.course.save()

        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('course_detail', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/level_locked.html')


class EnrollmentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.free_course = Course.objects.create(
            title="Free Course",
            description="Free course",
            is_published=True,
            required_level=0,
            price=0
        )

        self.paid_course = Course.objects.create(
            title="Paid Course",
            description="Paid course",
            is_published=True,
            required_level=0,
            price=49.99
        )

    def test_enroll_free_course_requires_login(self):
        """Test anonymous users cannot enroll"""
        response = self.client.get(reverse('enroll_course', args=[self.free_course.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_enroll_free_course_success(self):
        """Test enrolled in free course"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('enroll_course', args=[self.free_course.id]))

        # Should redirect to course detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.free_course.id]))

        # Check enrollment was created
        self.assertTrue(Enrollment.objects.filter(
            user=self.user,
            course=self.free_course
        ).exists())

        # Check XP was awarded
        self.assertTrue(XPEvent.objects.filter(
            user=self.user,
            points=25,
            reason__contains='Enrolled'
        ).exists())

    def test_enroll_paid_course_redirects_to_checkout(self):
        """Test paid course redirects to checkout"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('enroll_course', args=[self.paid_course.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_checkout', args=[self.paid_course.id]))

        # Should not be enrolled yet
        self.assertFalse(Enrollment.objects.filter(
            user=self.user,
            course=self.paid_course
        ).exists())

    def test_cannot_enroll_twice(self):
        """Test user cannot enroll in same course twice"""
        self.client.login(email='test@example.com', password='testpass123')

        # First enrollment
        Enrollment.objects.create(user=self.user, course=self.free_course)

        # Try to enroll again
        response = self.client.get(reverse('enroll_course', args=[self.free_course.id]))

        # Should redirect with message
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.free_course.id]))

        # Still only one enrollment
        self.assertEqual(Enrollment.objects.filter(
            user=self.user,
            course=self.free_course
        ).count(), 1)


class LessonDetailViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Student'
        )

        # Create course structure
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            is_published=True,
            required_level=0,
            price=0
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Test Module",
            order=1
        )

        # Create two lessons (for next/previous navigation)
        self.lesson1 = Lesson.objects.create(
            module=self.module,
            title="Lesson 1",
            content="Content for lesson 1",
            order=1
        )

        self.lesson2 = Lesson.objects.create(
            module=self.module,
            title="Lesson 2",
            content="Content for lesson 2",
            order=2
        )

        # Enroll the user
        self.enrollment = Enrollment.objects.create(
            user=self.user,
            course=self.course
        )

    def test_lesson_detail_requires_login(self):
        """Test that anonymous users are redirected"""
        response = self.client.get(reverse('lesson_detail', args=[self.lesson1.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/accounts/login/', response.url)

    def test_lesson_detail_requires_enrollment(self):
        """Test that enrolled users can access lessons"""
        # Create a different user who is not enrolled
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        self.client.login(email='other@example.com', password='testpass123')

        response = self.client.get(reverse('lesson_detail', args=[self.lesson1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/not_enrolled.html')

    def test_lesson_detail_for_enrolled_user(self):
        """Test that enrolled users can view lessons"""
        self.client.login(email='student@example.com', password='testpass123')
        response = self.client.get(reverse('lesson_detail', args=[self.lesson1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/lesson_detail.html')
        self.assertContains(response, "Lesson 1")
        self.assertContains(response, "Content for lesson 1")

        # Check context data
        self.assertEqual(response.context['lesson'], self.lesson1)
        self.assertEqual(response.context['course'], self.course)
        self.assertFalse(response.context['is_completed'])

        # Check navigation
        self.assertIsNone(response.context['previous_lesson'])
        self.assertEqual(response.context['next_lesson'], self.lesson2)

    def test_lesson_completion_tracking(self):
        """Test that completed lessons show as completed"""
        self.client.login(email='student@example.com', password='testpass123')

        # Mark lesson as complete
        LessonCompletion.objects.create(
            user=self.user,
            lesson=self.lesson1
        )

        response = self.client.get(reverse('lesson_detail', args=[self.lesson1.id]))
        self.assertTrue(response.context['is_completed'])

        # Check progress calculations
        self.assertEqual(response.context['completed_count'], 1)
        self.assertEqual(response.context['total_lessons'], 2)
        self.assertEqual(response.context['progress_percentage'], 50)

    def test_lesson_navigation(self):
        """Test next/previous lesson navigation"""
        self.client.login(email='student@example.com', password='testpass123')

        # Test lesson1 -> next is lesson2
        response = self.client.get(reverse('lesson_detail', args=[self.lesson1.id]))
        self.assertEqual(response.context['next_lesson'], self.lesson2)
        self.assertIsNone(response.context['previous_lesson'])

        # Test lesson2 -> previous is lesson1
        response = self.client.get(reverse('lesson_detail', args=[self.lesson2.id]))
        self.assertEqual(response.context['previous_lesson'], self.lesson1)
        self.assertIsNone(response.context['next_lesson'])

    def test_lesson_comments_pagination(self):
        """Test that comments are paginated"""
        from courses.models import Comment

        self.client.login(email='student@example.com', password='testpass123')

        # Create 7 comments (more than 5 per page)
        for i in range(7):
            Comment.objects.create(
                lesson=self.lesson1,
                user=self.user,
                content=f"Test comment {i}"
            )

        response = self.client.get(reverse('lesson_detail', args=[self.lesson1.id]))

        # Check pagination
        self.assertEqual(response.context['total_comments'], 7)
        self.assertEqual(len(response.context['comments']), 5)  # First page has 5

        # Check that comment form is present - using your actual text
        self.assertContains(response, "Add a comment or question:")
        self.assertContains(response, "Post Comment")

    def test_comment_form_submission(self):
        """Test posting a comment"""
        self.client.login(email='student@example.com', password='testpass123')

        # Post a comment
        response = self.client.post(reverse('lesson_detail', args=[self.lesson1.id]), {
            'comment_submit': '1',
            'content': 'This is a test comment'
        })

        # Should redirect back to lesson
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('lesson_detail', args=[self.lesson1.id]))

        # Check comment was created
        from courses.models import Comment
        comment = Comment.objects.filter(lesson=self.lesson1).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.content, 'This is a test comment')
        self.assertEqual(comment.user, self.user)


class MarkLessonCompleteTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='student@example.com',
            password='testpass123'
        )

        # Create course structure
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            is_published=True,
            required_level=0,
            price=0
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Test Module",
            order=1
        )

        self.lesson1 = Lesson.objects.create(
            module=self.module,
            title="Lesson 1",
            content="Content for lesson 1",
            order=1
        )

        self.lesson2 = Lesson.objects.create(
            module=self.module,
            title="Lesson 2",
            content="Content for lesson 2",
            order=2
        )

        # Enroll the user
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.login(email='student@example.com', password='testpass123')

    def test_mark_lesson_complete(self):
        """Test marking a lesson as complete"""
        response = self.client.get(reverse('mark_lesson_complete', args=[self.lesson1.id]))

        # Should redirect to next lesson
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('lesson_detail', args=[self.lesson2.id]))

        # Check completion was created
        completion = LessonCompletion.objects.filter(
            user=self.user,
            lesson=self.lesson1
        ).first()
        self.assertIsNotNone(completion)

        # Check XP was awarded
        xp_event = XPEvent.objects.filter(
            user=self.user,
            points=10,
            reason__contains='Completed lesson'
        ).first()
        self.assertIsNotNone(xp_event)

    def test_cannot_complete_lesson_twice(self):
        """Test marking same lesson complete twice doesn't double XP"""
        # First completion
        self.client.get(reverse('mark_lesson_complete', args=[self.lesson1.id]))

        # Second completion
        self.client.get(reverse('mark_lesson_complete', args=[self.lesson1.id]))

        # Should only have one completion
        self.assertEqual(
            LessonCompletion.objects.filter(user=self.user, lesson=self.lesson1).count(),
            1
        )

        # Should only have one XP event
        self.assertEqual(
            XPEvent.objects.filter(user=self.user, points=10).count(),
            1
        )

    def test_complete_last_lesson_redirects_to_course_completed(self):
        """Test completing the last lesson redirects to course completed page"""
        # Complete first lesson
        self.client.get(reverse('mark_lesson_complete', args=[self.lesson1.id]))

        # Complete second lesson
        response = self.client.get(reverse('mark_lesson_complete', args=[self.lesson2.id]))

        # Should redirect to course completed
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_completed', args=[self.course.id]))
