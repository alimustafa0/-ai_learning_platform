from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import User, Follow

class UserModelTests(TestCase):
    def setUp(self):
        """Create test users before each test"""
        self.user1 = User.objects.create_user(
            email='test1@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith'
        )

    def test_create_user(self):
        """Test that a user is created correctly"""
        self.assertEqual(self.user1.email, 'test1@example.com')
        self.assertTrue(self.user1.check_password('testpass123'))
        self.assertEqual(self.user1.get_full_name(), 'John Doe')
        self.assertEqual(self.user1.get_short_name(), 'John')

    def test_user_string_representation(self):
        """Test the string representation of a user"""
        self.assertEqual(str(self.user1), 'test1@example.com (John Doe)')

        # Test user with no name
        user3 = User.objects.create_user(
            email='test3@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user3), 'test3@example.com')

    def test_follow_functionality(self):
        """Test that users can follow each other"""
        # Create a follow relationship
        follow = Follow.objects.create(
            follower=self.user1,
            following=self.user2
        )

        # Test the relationship
        self.assertEqual(self.user1.following.count(), 1)
        self.assertEqual(self.user2.followers.count(), 1)
        self.assertEqual(follow.follower, self.user1)
        self.assertEqual(follow.following, self.user2)

        # Test the string representation
        self.assertEqual(str(follow), 'test1@example.com follows test2@example.com')

    def test_unique_follow(self):
        """Test that a user cannot follow the same user twice"""
        Follow.objects.create(
            follower=self.user1,
            following=self.user2
        )

        # Try to create duplicate follow - should raise an error
        with self.assertRaises(Exception):
            Follow.objects.create(
                follower=self.user1,
                following=self.user2
            )
