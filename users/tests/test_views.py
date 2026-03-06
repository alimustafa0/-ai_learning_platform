from django.test import TestCase, Client
from django.urls import reverse
from users.models import User, Follow
from courses.models import XPEvent

class ProfileViewTests(TestCase):
    def setUp(self):
        """Create test client and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_profile_view_requires_login(self):
        """Test that profile page redirects anonymous users"""
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/accounts/login/', response.url)

    def test_profile_view_for_logged_in_user(self):
        """Test that logged in user can see their profile"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Test User')

    def test_profile_edit_view(self):
        """Test that user can access profile edit page"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('profile_edit'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        """Test that user can update their profile"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('profile_edit'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'This is my bio',
            'location': 'Test City',
            'website': 'https://example.com',
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertRedirects(response, reverse('profile_view'))

        # Check that user was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.bio, 'This is my bio')

class PublicProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User'
        )

    def test_public_profile_view(self):
        """Test that public profile is accessible"""
        response = self.client.get(reverse('public_profile', args=['other@example.com']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Other User')

    def test_public_profile_404_for_nonexistent_user(self):
        """Test that non-existent user returns 404"""
        response = self.client.get(reverse('public_profile', args=['nonexistent@example.com']))
        self.assertEqual(response.status_code, 404)

class FollowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass123'
        )
        self.client.login(email='user1@example.com', password='testpass123')

    def test_follow_user(self):
        """Test following another user"""
        response = self.client.post(reverse('toggle_follow', args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['is_following'], True)

        # Check follow was created
        self.assertTrue(Follow.objects.filter(
            follower=self.user1,
            following=self.user2
        ).exists())

        # Check XP was awarded
        self.assertTrue(XPEvent.objects.filter(
            user=self.user1,
            points=1,
            reason__contains='Followed'
        ).exists())

    def test_unfollow_user(self):
        """Test unfollowing a user"""
        # First follow
        Follow.objects.create(follower=self.user1, following=self.user2)

        # Then unfollow
        response = self.client.post(reverse('toggle_follow', args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['is_following'], False)

        # Check follow was deleted
        self.assertFalse(Follow.objects.filter(
            follower=self.user1,
            following=self.user2
        ).exists())

    def test_cannot_follow_self(self):
        """Test that user cannot follow themselves"""
        response = self.client.post(reverse('toggle_follow', args=[self.user1.id]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_following_list_view(self):
        """Test following list page"""
        Follow.objects.create(follower=self.user1, following=self.user2)
        response = self.client.get(reverse('following_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user2@example.com')

    def test_followers_list_view(self):
        """Test followers list page"""
        Follow.objects.create(follower=self.user2, following=self.user1)
        response = self.client.get(reverse('followers_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user2@example.com')
