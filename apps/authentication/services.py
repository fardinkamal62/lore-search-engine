import logging

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service for authentication related operations"""
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PermissionService:
    """Service for handling permissions and authorization"""

    ROLE_PERMISSIONS = {
        'admin': [
            'can_manage_users',
            'can_manage_content',
            'can_view_analytics',
            'can_manage_system',
            'can_upload_files',
            'can_search',
        ],
        'editor': [
            'can_manage_content',
            'can_upload_files',
            'can_search',
        ],
        'contributor': [
            'can_upload_files',
            'can_search',
        ],
        'viewer': [
            'can_search',
        ],
    }

    @staticmethod
    def user_has_permission(user, permission):
        """Check if user has specific permission"""
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Default to viewer permissions for regular users
        viewer_permissions = PermissionService.ROLE_PERMISSIONS.get('viewer', [])
        return permission in viewer_permissions

    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for user"""
        if not user or not user.is_authenticated:
            return []

        if user.is_superuser:
            # Return all permissions
            all_perms = []
            for perms in PermissionService.ROLE_PERMISSIONS.values():
                all_perms.extend(perms)
            return list(set(all_perms))

        # Default to viewer permissions for regular users
        return PermissionService.ROLE_PERMISSIONS.get('viewer', [])
