from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from decimal import Decimal
from courses.models import (
    Course, Module, Lesson, Enrollment,
    Review, XPEvent, Achievement, UserAchievement
)
from users.models import User

User = get_user_model()

class ReviewSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Student'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User'
        )

        # Create a course
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            is_published=True,
            required_level=0,
            price=Decimal('0.00')
        )

        # Enroll the main user
        self.enrollment = Enrollment.objects.create(
            user=self.user,
            course=self.course
        )

        self.client.login(email='student@example.com', password='testpass123')

    def test_add_review_view_loads(self):
        """Test that add review page loads for enrolled user"""
        response = self.client.get(reverse('add_review', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/review_form.html')
        self.assertContains(response, "Test Course")
        self.assertIn('form', response.context)

    def test_add_review_requires_enrollment(self):
        """Test that non-enrolled users cannot review"""
        # Create a new course without enrolling
        new_course = Course.objects.create(
            title="New Course",
            description="No enrollment",
            is_published=True,
            price=Decimal('0.00')
        )

        response = self.client.get(reverse('add_review', args=[new_course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[new_course.id]))

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("must be enrolled" in str(m) for m in messages))

    def test_add_review_requires_login(self):
        """Test that anonymous users are redirected"""
        self.client.logout()
        response = self.client.get(reverse('add_review', args=[self.course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_submit_new_review(self):
        """Test submitting a new review"""
        response = self.client.post(reverse('add_review', args=[self.course.id]), {
            'rating': 5,
            'comment': 'This is an excellent course! Very informative.'
        })

        # Should redirect to course detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.course.id]))

        # Check review was created
        review = Review.objects.filter(
            user=self.user,
            course=self.course
        ).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'This is an excellent course! Very informative.')

        # Check XP was awarded (5 points for new review)
        xp_event = XPEvent.objects.filter(
            user=self.user,
            points=5,
            reason__contains='Reviewed'
        ).first()
        self.assertIsNotNone(xp_event)

    def test_edit_existing_review(self):
        """Test editing an existing review"""
        # Create a review by submitting the form
        response = self.client.post(reverse('add_review', args=[self.course.id]), {
            'rating': 3,
            'comment': 'It was okay.'
        })

        # Should redirect after creation
        self.assertEqual(response.status_code, 302)

        # Verify XP was created for the new review
        xp_count_before_edit = XPEvent.objects.filter(
            user=self.user,
            points=5,
            reason__contains='Reviewed'
        ).count()
        self.assertEqual(xp_count_before_edit, 1)  # XP awarded for creation

        # Get the review that was created
        review = Review.objects.get(user=self.user, course=self.course)
        self.assertEqual(review.rating, 3)
        self.assertEqual(review.comment, 'It was okay.')

        # Now edit it
        response = self.client.post(reverse('add_review', args=[self.course.id]), {
            'rating': 4,
            'comment': 'Actually, it was pretty good!'
        })

        self.assertEqual(response.status_code, 302)

        # Check review was updated
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, 'Actually, it was pretty good!')

        # Should not award XP again for edit
        xp_events = XPEvent.objects.filter(
            user=self.user,
            points=5
        )
        self.assertEqual(xp_events.count(), 1)  # Still only one XP event

    def test_review_form_validation(self):
        """Test that invalid review data is rejected"""
        response = self.client.post(reverse('add_review', args=[self.course.id]), {
            'rating': 6,  # Invalid rating (should be 1-5)
            'comment': ''
        })

        # Should stay on form page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/review_form.html')

        # Check form has errors
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('rating', form.errors)
        self.assertIn('valid rating', str(form.errors['rating']))

        # No review should be created
        self.assertEqual(Review.objects.filter(user=self.user).count(), 0)

    def test_delete_review(self):
        """Test deleting a review"""
        # Create a review first
        review = Review.objects.create(
            user=self.user,
            course=self.course,
            rating=5,
            comment='Great course!'
        )

        # Delete it
        response = self.client.post(reverse('delete_review', args=[review.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.course.id]))

        # Check it's gone
        self.assertEqual(Review.objects.filter(id=review.id).count(), 0)

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted" in str(m) for m in messages))

    def test_cannot_delete_others_review(self):
        """Test that users cannot delete others' reviews"""
        # Create a review by other user
        review = Review.objects.create(
            user=self.other_user,
            course=self.course,
            rating=5,
            comment='Great course!'
        )

        # Try to delete it
        response = self.client.post(reverse('delete_review', args=[review.id]))

        # Should get 404 (since get_object_or_404 filters by user=request.user)
        self.assertEqual(response.status_code, 404)

        # Review should still exist
        self.assertEqual(Review.objects.filter(id=review.id).count(), 1)

    def test_helpful_vote_on_review(self):
        """Test voting a review as helpful"""
        # Create a review by other user
        review = Review.objects.create(
            user=self.other_user,
            course=self.course,
            rating=5,
            comment='Great course!'
        )

        # Vote as helpful
        response = self.client.post(reverse('helpful_review', args=[review.id]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'added')
        self.assertEqual(data['total_helpful'], 1)
        self.assertTrue(data['user_helpful'])

        # Check that vote was recorded
        self.assertTrue(review.helpful_votes.filter(id=self.user.id).exists())

    def test_remove_helpful_vote(self):
        """Test removing a helpful vote"""
        # Create a review by other user
        review = Review.objects.create(
            user=self.other_user,
            course=self.course,
            rating=5,
            comment='Great course!'
        )

        # Add vote first
        review.helpful_votes.add(self.user)
        self.assertEqual(review.helpful_votes.count(), 1)

        # Remove vote
        response = self.client.post(reverse('helpful_review', args=[review.id]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'removed')
        self.assertEqual(data['total_helpful'], 0)
        self.assertFalse(data['user_helpful'])

        # Check that vote was removed
        self.assertFalse(review.helpful_votes.filter(id=self.user.id).exists())

    def test_cannot_vote_on_own_review(self):
        """Test that users cannot vote on their own reviews"""
        # Create a review by current user
        review = Review.objects.create(
            user=self.user,
            course=self.course,
            rating=5,
            comment='My own review'
        )

        # Try to vote
        response = self.client.post(reverse('helpful_review', args=[review.id]))

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'You cannot vote on your own review')

    def test_helpful_vote_milestone_xp(self):
        """Test that reaching 5 helpful votes awards XP"""
        # Create a review by other user
        review = Review.objects.create(
            user=self.other_user,
            course=self.course,
            rating=5,
            comment='Great course!'
        )

        # Need 4 other users to vote
        users = []
        for i in range(4):
            user = User.objects.create_user(
                email=f'user{i}@example.com',
                password='testpass123'
            )
            users.append(user)
            review.helpful_votes.add(user)

        # Current user's vote should be the 5th
        self.assertEqual(review.helpful_votes.count(), 4)

        response = self.client.post(reverse('helpful_review', args=[review.id]))

        self.assertEqual(response.status_code, 200)

        # Check that XP was awarded to review author
        xp_event = XPEvent.objects.filter(
            user=self.other_user,
            points=10,
            reason__contains='helping others'
        ).first()
        self.assertIsNotNone(xp_event)

    def test_review_appears_in_course_detail(self):
        """Test that reviews appear on course detail page"""
        # Create a review
        review = Review.objects.create(
            user=self.user,
            course=self.course,
            rating=5,
            comment='Excellent course!'
        )

        # View course detail
        response = self.client.get(reverse('course_detail', args=[self.course.id]))

        self.assertContains(response, 'Excellent course!')
        self.assertContains(response, '5')
        self.assertContains(response, 'Test Student')
