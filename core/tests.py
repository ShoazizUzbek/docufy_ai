from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Organization, User


class UserModelTests(TestCase):
    def test_create_user_normalizes_email_and_sets_password(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = User.objects.create_user(email='Person@Example.com', password='pw12345', organization=org)
        self.assertEqual(user.email, 'Person@example.com')
        self.assertTrue(user.check_password('pw12345'))
        self.assertEqual(user.organization, org)

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pw12345')


class AuthAPITests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.user = User.objects.create_user(
            email='user@acme.com', password='pw12345', organization=self.org,
        )

    def test_login_returns_tokens_and_user(self):
        response = self.client.post(
            reverse('auth-login'), {'email': 'user@acme.com', 'password': 'pw12345'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'user@acme.com')
        self.assertEqual(response.data['user']['organization']['slug'], 'acme')

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse('auth-login'), {'email': 'user@acme.com', 'password': 'wrong'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        login = self.client.post(
            reverse('auth-login'), {'email': 'user@acme.com', 'password': 'pw12345'},
        )
        access = login.data['access']
        response = self.client.get(
            reverse('auth-me'), HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user@acme.com')
