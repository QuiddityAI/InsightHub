from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse


class SignupViewTestCase(TestCase):
    def setUp(self):
        # Clean up any existing users
        User.objects.all().delete()

    @override_settings(IS_ON_PREMISE=True)
    def test_signup_disabled_when_on_premise(self):
        """Test that signup is disabled when IS_ON_PREMISE is True"""
        response = self.client.post('/org/signup_from_app/', {
            'email': 'test@example.com',
            'password': 'testpassword123'
        })

        # Should return 403 Forbidden when registration is disabled
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Registration is disabled', response.content)

        # User should not be created
        self.assertFalse(User.objects.filter(username='test@example.com').exists())

    @override_settings(IS_ON_PREMISE=False)
    def test_signup_enabled_when_not_on_premise(self):
        """Test that signup works normally when IS_ON_PREMISE is False"""
        response = self.client.post('/org/signup_from_app/', {
            'email': 'test@example.com',
            'password': 'testpassword123'
        })

        # Should redirect (normal signup behavior)
        self.assertEqual(response.status_code, 302)

        # User should be created
        self.assertTrue(User.objects.filter(username='test@example.com').exists())

    def test_signup_default_behavior(self):
        """Test that signup works normally when IS_ON_PREMISE is not set (default behavior)"""
        response = self.client.post('/org/signup_from_app/', {
            'email': 'test@example.com',
            'password': 'testpassword123'
        })

        # Should redirect (normal signup behavior)
        self.assertEqual(response.status_code, 302)

        # User should be created
        self.assertTrue(User.objects.filter(username='test@example.com').exists())
