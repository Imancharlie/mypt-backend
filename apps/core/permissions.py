from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.student == request.user or obj.user == request.user


class IsProfileComplete(permissions.BasePermission):
    """
    Custom permission to check if user profile is complete.
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and request.user.profile.company is not None


class IsCompanyOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for company objects.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to admin users
        return request.user.is_staff 