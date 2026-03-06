from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock
from decimal import Decimal
from courses.models import Course, Enrollment, Payment, XPEvent
from users.models import User
from config import settings

User = get_user_model()

class PaymentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Student'
        )
        self.client.login(email='student@example.com', password='testpass123')

        # Create a paid course
        self.course = Course.objects.create(
            title="Paid Course",
            description="This is a paid course",
            is_published=True,
            required_level=0,
            price=Decimal('49.99')
        )

        # Create a free course
        self.free_course = Course.objects.create(
            title="Free Course",
            description="This is a free course",
            is_published=True,
            required_level=0,
            price=Decimal('0.00')
        )

    def test_course_checkout_view(self):
        """Test checkout page loads for paid course"""
        response = self.client.get(reverse('course_checkout', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_checkout.html')
        self.assertContains(response, "Paid Course")
        self.assertContains(response, "$49.99")
        self.assertIn('stripe_public_key', response.context)

    def test_course_checkout_redirects_for_free_course(self):
        """Test free courses redirect to enrollment"""
        response = self.client.get(reverse('course_checkout', args=[self.free_course.id]))
        self.assertEqual(response.status_code, 302)

        # Follow all redirects to the final page
        final_response = self.client.get(response.url, follow=True)
        self.assertEqual(final_response.status_code, 200)
        self.assertTemplateUsed(final_response, 'courses/course_detail.html')

        # Verify we ended up on the correct course detail page
        self.assertEqual(final_response.context['course'], self.free_course)

    def test_course_checkout_redirects_if_already_enrolled(self):
        """Test already enrolled users are redirected"""
        Enrollment.objects.create(user=self.user, course=self.course)
        response = self.client.get(reverse('course_checkout', args=[self.course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.course.id]))

        # Check message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already enrolled" in str(m) for m in messages))

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_success(self, mock_stripe_create):
        """Test successful creation of Stripe checkout session"""
        # Mock Stripe response
        mock_session = MagicMock()
        mock_session.id = "cs_test_123456"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_session.payment_intent = "pi_test_123456"
        mock_stripe_create.return_value = mock_session

        response = self.client.get(reverse('create_checkout_session', args=[self.course.id]))

        # Should redirect to Stripe
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.com/test")

        # Check payment record was created
        payment = Payment.objects.filter(
            user=self.user,
            course=self.course,
            status='pending'
        ).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.stripe_checkout_session_id, "cs_test_123456")
        self.assertEqual(payment.amount, Decimal('49.99'))
        self.assertEqual(payment.currency, "USD")

        # Verify Stripe was called correctly
        mock_stripe_create.assert_called_once()
        call_kwargs = mock_stripe_create.call_args[1]
        self.assertEqual(call_kwargs['customer_email'], 'student@example.com')
        self.assertEqual(call_kwargs['metadata']['course_id'], str(self.course.id))
        self.assertEqual(call_kwargs['metadata']['user_id'], str(self.user.id))
        self.assertEqual(call_kwargs['line_items'][0]['price_data']['unit_amount'], 4999)  # $49.99 * 100

    def test_create_checkout_session_redirects_if_already_enrolled(self):
        """Test enrolled users can't create checkout session"""
        Enrollment.objects.create(user=self.user, course=self.course)
        response = self.client.get(reverse('create_checkout_session', args=[self.course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.course.id]))

    def test_create_checkout_session_redirects_for_free_course(self):
        """Test free courses redirect to enrollment"""
        response = self.client.get(reverse('create_checkout_session', args=[self.free_course.id]))
        self.assertEqual(response.status_code, 302)

        # Follow all redirects to the final page
        final_response = self.client.get(response.url, follow=True)
        self.assertEqual(final_response.status_code, 200)
        self.assertTemplateUsed(final_response, 'courses/course_detail.html')

        # Verify we ended up on the correct course detail page
        self.assertEqual(final_response.context['course'], self.free_course)

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_handles_stripe_error(self, mock_stripe_create):
        """Test error handling when Stripe fails"""
        mock_stripe_create.side_effect = Exception("Stripe API error")

        response = self.client.get(reverse('create_checkout_session', args=[self.course.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_checkout', args=[self.course.id]))

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Payment error" in str(m) for m in messages))

    @patch('stripe.checkout.Session.retrieve')
    def test_payment_success_enrolls_user(self, mock_stripe_retrieve):
        """Test successful payment enrolls user"""
        # Create a pending payment first
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            stripe_checkout_session_id="cs_test_123456",
            stripe_payment_intent_id="pi_test_123456",
            amount=Decimal('49.99'),
            currency="USD",
            status="pending"
        )

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.payment_intent = "pi_test_123456"
        mock_session.metadata = {
            'user_id': str(self.user.id),
            'course_id': str(self.course.id)
        }
        mock_stripe_retrieve.return_value = mock_session

        response = self.client.get(
            reverse('payment_success', args=[self.course.id]),
            {'session_id': 'cs_test_123456'}
        )

        # Should redirect to course detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', args=[self.course.id]))

        # Check payment was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")

        # Check user was enrolled
        self.assertTrue(Enrollment.objects.filter(
            user=self.user,
            course=self.course
        ).exists())

        # Check XP was awarded
        xp_events = XPEvent.objects.filter(user=self.user)
        self.assertGreaterEqual(xp_events.count(), 1)

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Payment successful" in str(m) for m in messages))

    @patch('stripe.checkout.Session.retrieve')
    def test_payment_success_handles_existing_enrollment(self, mock_stripe_retrieve):
        """Test payment success works even if user somehow already enrolled"""
        # Enroll user first
        Enrollment.objects.create(user=self.user, course=self.course)

        # Create pending payment
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            stripe_checkout_session_id="cs_test_123456",
            stripe_payment_intent_id="pi_test_123456",
            amount=Decimal('49.99'),
            currency="USD",
            status="pending"
        )

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.payment_intent = "pi_test_123456"
        mock_session.metadata = {
            'user_id': str(self.user.id),
            'course_id': str(self.course.id)
        }
        mock_stripe_retrieve.return_value = mock_session

        response = self.client.get(
            reverse('payment_success', args=[self.course.id]),
            {'session_id': 'cs_test_123456'}
        )

        self.assertEqual(response.status_code, 302)

        # Should still have only one enrollment
        self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)

    @patch('stripe.checkout.Session.retrieve')
    def test_payment_success_verifies_user_id(self, mock_stripe_retrieve):
        """Test payment success verifies the session belongs to correct user"""
        mock_session = MagicMock()
        mock_session.metadata = {
            'user_id': '999',  # Wrong user ID
            'course_id': str(self.course.id)
        }
        mock_stripe_retrieve.return_value = mock_session

        response = self.client.get(
            reverse('payment_success', args=[self.course.id]),
            {'session_id': 'cs_test_123456'}
        )

        self.assertEqual(response.status_code, 302)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("doesn't belong to you" in str(m) for m in messages))

    @patch('stripe.checkout.Session.retrieve')
    def test_payment_success_verifies_course_id(self, mock_stripe_retrieve):
        """Test payment success verifies the session is for correct course"""
        other_course = Course.objects.create(
            title="Other Course",
            description="Different course",
            is_published=True,
            price=Decimal('29.99')
        )

        mock_session = MagicMock()
        mock_session.metadata = {
            'user_id': str(self.user.id),
            'course_id': str(other_course.id)  # Wrong course
        }
        mock_stripe_retrieve.return_value = mock_session

        response = self.client.get(
            reverse('payment_success', args=[self.course.id]),
            {'session_id': 'cs_test_123456'}
        )

        self.assertEqual(response.status_code, 302)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("course mismatch" in str(m) for m in messages))

    def test_payment_success_requires_session_id(self):
        """Test payment success requires session_id parameter"""
        response = self.client.get(reverse('payment_success', args=[self.course.id]))
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid payment session" in str(m) for m in messages))

    def test_payment_receipt_view(self):
        """Test payment receipt page loads"""
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            stripe_checkout_session_id="cs_test_123456",
            stripe_payment_intent_id="pi_test_123456",
            amount=Decimal('49.99'),
            currency="USD",
            status="succeeded"
        )

        response = self.client.get(reverse('payment_receipt', args=[payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/payment_receipt.html')
        self.assertEqual(response.context['payment'], payment)
        self.assertIn('receipt', response.context)

    def test_payment_receipt_requires_ownership(self):
        """Test users can only see their own receipts"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )

        payment = Payment.objects.create(
            user=other_user,
            course=self.course,
            stripe_checkout_session_id="cs_test_123456",
            stripe_payment_intent_id="pi_test_123456",
            amount=Decimal('49.99'),
            currency="USD",
            status="succeeded"
        )

        response = self.client.get(reverse('payment_receipt', args=[payment.id]))
        self.assertEqual(response.status_code, 404)  # Your view returns 404

    def test_payment_receipt_404_for_nonexistent(self):
        """Test nonexistent payment returns 404"""
        response = self.client.get(reverse('payment_receipt', args=[999]))
        self.assertEqual(response.status_code, 404)
