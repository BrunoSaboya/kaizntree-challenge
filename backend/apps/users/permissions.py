from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "owner"


class IsOrgUser(BasePermission):
    """Passes for owner and member; blocks admin (who has organization=None)."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.organization_id is not None
        )
