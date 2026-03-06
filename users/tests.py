from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages

from users.forms import CustomUserCreationForm, UserProfileForm

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

    def test_user_ordering(self):
        """Test that users are ordered correctly"""
        # Create users in non-alphabetical order
        User.objects.create_user(
            email="b@example.com",
            password="testpass123",
            first_name="Beta"
        )
        User.objects.create_user(
            email="a@example.com",
            password="testpass123",
            first_name="Alpha"
        )

        users = User.objects.all()
        # First user should be a@example.com (alphabetical by email)
        self.assertEqual(users[0].email, "a@example.com")
        self.assertEqual(users[1].email, "b@example.com")

    def test_profile_field_help_text(self):
        """Test that profile fields have proper help text"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )

        # Check field help texts
        bio_field = user._meta.get_field('bio')
        self.assertIn('max 500 characters', bio_field.help_text)

        website_field = user._meta.get_field('website')
        self.assertIn('Optional', website_field.help_text)

        location_field = user._meta.get_field('location')
        self.assertEqual(location_field.help_text, "City, Country")

class UserFormsTest(TestCase):
    def test_registration_form_valid_data(self):
        """Test registration form with valid data"""
        form_data = {
            'email': 'newuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'testpass123',
            'password2': 'testpass123',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_registration_form_missing_first_name(self):
        """Test registration fails without first name"""
        form_data = {
            'email': 'newuser@example.com',
            'last_name': 'Doe',
            'password1': 'testpass123',
            'password2': 'testpass123',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_registration_form_password_mismatch(self):
        """Test registration fails when passwords don't match"""
        form_data = {
            'email': 'newuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'testpass123',
            'password2': 'differentpass123',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_profile_form_valid_data(self):
        """Test profile form with valid data"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'This is my bio',
            'website': 'https://example.com',
            'location': 'New York',
        }
        form = UserProfileForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())

    def test_profile_form_avatar_size_validation(self):
        """Test that avatar file size is validated"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a mock file that's too large (3MB)
        mock_image = SimpleUploadedFile(
            "large.jpg",
            b"x" * (3 * 1024 * 1024),  # 3MB
            content_type="image/jpeg"
        )

        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
        }
        form_files = {'avatar': mock_image}

        form = UserProfileForm(data=form_data, files=form_files, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_profile_form_avatar_extension_validation(self):
        """Test that avatar file extension is validated"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a mock file with invalid extension
        mock_file = SimpleUploadedFile(
            "malicious.exe",
            b"fake image content",
            content_type="application/x-msdownload"
        )

        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
        }
        form_files = {'avatar': mock_file}

        form = UserProfileForm(data=form_data, files=form_files, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_profile_form_website_validation(self):
        """Test that website URL is properly validated"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        # Test invalid URL
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'website': 'not-a-valid-url',
        }
        form = UserProfileForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('website', form.errors)

        # Test URL without protocol (should be accepted and normalized)
        form_data = {
            'website': 'example.com',
        }
        form = UserProfileForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        # Check that protocol was added
        self.assertEqual(form.cleaned_data['website'], 'https://example.com')


class UserViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_signup_view_get(self):
        """Test signup page loads"""
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/signup.html')

    def test_signup_view_post_success(self):
        """Test user can sign up successfully"""
        response = self.client.post(reverse('signup'), {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        # Should redirect to dashboard
        self.assertRedirects(response, reverse('dashboard'))
        # Check user was created
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_profile_view_requires_login(self):
        """Test profile view redirects anonymous users"""
        response = self.client.get(reverse('profile_view'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile_view')}")

    def test_profile_view_authenticated(self):
        """Test authenticated user can view profile"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')
        self.assertEqual(response.context['profile_user'], self.user)

    def test_profile_edit_view_requires_login(self):
        """Test profile edit view redirects anonymous users"""
        response = self.client.get(reverse('profile_edit'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile_edit')}")

    def test_profile_edit_update_success(self):
        """Test user can update profile"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('profile_edit'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'This is my new bio',
            'website': 'https://example.com',
            'location': 'New York',
        })
        # Should redirect to profile view
        self.assertRedirects(response, reverse('profile_view'))

        # Check user was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.bio, 'This is my new bio')

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(msg.message == 'Your profile has been updated!' for msg in messages))
