from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class UserModelTests(TestCase):
    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful"""
        email = "test@example.com"
        password = "testpass123"
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="John",
            last_name="Doe"
        )
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_user_without_email_fails(self):
        """Test creating a user without an email raises error"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="testpass123")
    
    def test_create_superuser_successful(self):
        """Test creating a superuser is successful"""
        email = "admin@example.com"
        password = "adminpass123"
        user = User.objects.create_superuser(
            email=email,
            password=password
        )
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_user_string_representation(self):
        """Test the string representation of the user"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
        )
        
        # Should show email with name in parentheses
        self.assertEqual(str(user), "test@example.com (John Doe)")
        
        # Test with no name
        user2 = User.objects.create_user(
            email="noname@example.com",
            password="testpass123"
        )
        self.assertEqual(str(user2), "noname@example.com")

    def test_create_user_without_password_fails(self):
        """Test creating a user without a password raises error"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="test@example.com",
                password=None
            )