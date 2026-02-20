from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import re

User = get_user_model()


class AuthUtils:
    """Utility functions for authentication operations"""

    @staticmethod
    def validate_email_format(email):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None

    @staticmethod
    def is_email_unique(email, exclude_user=None):
        """Check if email is unique"""
        queryset = User.objects.filter(email=email)
        if exclude_user:
            queryset = queryset.exclude(id=exclude_user.id)
        return not queryset.exists()

    @staticmethod
    def is_username_unique(username, exclude_user=None):
        """Check if username is unique"""
        queryset = User.objects.filter(username=username)
        if exclude_user:
            queryset = queryset.exclude(id=exclude_user.id)
        return not queryset.exists()

    @staticmethod
    def validate_password_strength(password):
        """Validate password using Django's validators"""
        try:
            validate_password(password)
            return True, None
        except ValidationError as e:
            return False, e.messages

    @staticmethod
    def generate_user_token(user):
        """Generate or get existing token for user"""
        token, created = Token.objects.get_or_create(user=user)
        return token

    @staticmethod
    def revoke_user_token(user):
        """Revoke user's token"""
        try:
            token = Token.objects.get(user=user)
            token.delete()
            return True
        except Token.DoesNotExist:
            return False

    @staticmethod
    def refresh_user_token(user):
        """Refresh user's token (delete old, create new)"""
        # Delete existing token
        Token.objects.filter(user=user).delete()
        # Create new token
        token = Token.objects.create(user=user)
        return token

    @staticmethod
    def get_user_by_token(token_key):
        """Get user by token key"""
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None


class UserUtils:
    """Utility functions for user operations"""

    @staticmethod
    def create_user_with_profile(username, email, password, **extra_fields):
        """Create user with additional profile data"""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields
        )
        return user

    @staticmethod
    def update_user_profile(user, **update_fields):
        """Update user profile fields"""
        for field, value in update_fields.items():
            if hasattr(user, field):
                setattr(user, field, value)
        user.save()
        return user

    @staticmethod
    def deactivate_user(user):
        """Deactivate user account"""
        user.is_active = False
        user.save()
        # Also revoke token
        AuthUtils.revoke_user_token(user)
        return user

    @staticmethod
    def activate_user(user):
        """Activate user account"""
        user.is_active = True
        user.save()
        return user

    @staticmethod
    def get_user_stats():
        """Get basic user statistics"""
        return {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
        }
