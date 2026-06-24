from django_otp import user_has_device
from rest_framework.permissions import BasePermission


def staff_user_is_verified(user) -> bool:
    """OTP is required only when the user has a registered 2FA device."""
    if not user_has_device(user):
        return True
    verified = getattr(user, "is_verified", None)
    if callable(verified):
        return verified()
    return False


def client_user_is_verified(request, user) -> bool:
    """OTP completion state exposed to the SPA."""
    if not user_has_device(user):
        return True
    verified = getattr(user, "is_verified", None)
    if callable(verified):
        return verified()
    from django_otp import DEVICE_ID_SESSION_KEY

    return DEVICE_ID_SESSION_KEY in request.session


class IsStaffUser(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and staff_user_is_verified(user),
        )


class IsAuthenticatedStaff(BasePermission):
    """Staff session check without requiring completed 2FA (for /me during OTP step)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class IsSuperuserForSecrets(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)
