"""
Custom middleware for adding security headers.
Adds Content-Security-Policy and Permissions-Policy headers.
"""
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add Content-Security-Policy and Permissions-Policy headers.
    Works alongside nginx headers for comprehensive security.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        # Content-Security-Policy
        # Allow: self, Bootstrap CDN, inline scripts/styles for CKEditor
        # Note: 'unsafe-inline' is needed for CKEditor, consider using nonces in future
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Allow CSP to be overridden via environment variable
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', csp_policy)
        if csp:
            response['Content-Security-Policy'] = csp
        
        # Permissions-Policy (formerly Feature-Policy)
        # Restrict access to browser features
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
        
        # Allow Permissions-Policy to be overridden via environment variable
        pp = getattr(settings, 'PERMISSIONS_POLICY', permissions_policy)
        if pp:
            response['Permissions-Policy'] = pp
        
        return response

