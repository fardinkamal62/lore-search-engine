from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status

User = get_user_model()


class AuthenticationAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }

    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post('/api/auth/register/', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')

    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch"""
        data = self.user_data.copy()
        data['password_confirm'] = 'DifferentPass123!'
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        # Create first user
        User.objects.create_user(
            username='existing',
            email='test@example.com',
            password='TestPass123!'
        )
        # Try to register with same email
        response = self.client.post('/api/auth/register/', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login(self):
        """Test user login endpoint"""
        # Create user first
        User.objects.create_user(
            username='testuser',
            password='TestPass123!'
        )
        response = self.client.post('/api/auth/login/', self.login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/api/auth/login/', self.login_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_logout(self):
        """Test user logout endpoint"""
        # Create user and token
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!'
        )
        token = Token.objects.create(user=user)

        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Token should be deleted
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_user_profile_get(self):
        """Test getting user profile"""
        # Create user and token
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        token = Token.objects.create(user=user)

        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_user_profile_update(self):
        """Test updating user profile"""
        # Create user and token
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        token = Token.objects.create(user=user)

        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com'
        }

        response = self.client.put('/api/auth/profile/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')

    def test_token_refresh(self):
        """Test token refresh endpoint"""
        # Create user and token
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!'
        )
        old_token = Token.objects.create(user=user)

        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + old_token.key)

        response = self.client.post('/api/auth/token/refresh/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

        # Old token should be deleted
        self.assertFalse(Token.objects.filter(key=old_token.key).exists())
        # New token should exist
        self.assertTrue(Token.objects.filter(user=user).exists())

    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token"""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token')
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
