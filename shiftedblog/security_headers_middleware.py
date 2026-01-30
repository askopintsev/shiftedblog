"""
Custom middleware for security headers.
- Django 6: PermissionsPolicyMiddleware only (CSP via ContentSecurityPolicyMiddleware).
- Django < 6: SecurityHeadersMiddleware sets both CSP and Permissions-Policy.
"""
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    For Django < 6: sets Content-Security-Policy and Permissions-Policy.
    Used when django.utils.csp is not available.
    """
    def process_response(self, request, response):
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', None)
        if csp:
            response['Content-Security-Policy'] = csp
        pp = getattr(settings, 'PERMISSIONS_POLICY', None)
        if pp:
            response['Permissions-Policy'] = pp
        return response


class PermissionsPolicyMiddleware(MiddlewareMixin):
    """
    Middleware to add Permissions-Policy (formerly Feature-Policy) header.
    Restricts access to browser features for enhanced privacy.
    """
    def process_response(self, request, response):
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=(), "
            "vibrate=(), "
            "fullscreen=(self), "
            "payment=()"
        )
        pp = getattr(settings, 'PERMISSIONS_POLICY', permissions_policy)
        if pp:
            response['Permissions-Policy'] = pp
        return response
