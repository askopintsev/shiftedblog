"""
Rate-limited wrapper views for two-factor authentication.
Applies django-ratelimit decorators to authentication endpoints.
"""

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from two_factor.views import LoginView, QRGeneratorView, SetupView

# Rate limit: 10 requests per minute per IP (more lenient than nginx's 5/min)
# This allows for legitimate retries while still providing protection
RATE_LIMIT = "10/m"


# Rate-limited login view
@method_decorator(
    ratelimit(key="ip", rate=RATE_LIMIT, method=["GET", "POST"], block=True),
    name="dispatch",
)
class RateLimitedLoginView(LoginView):
    """Login view with rate limiting applied."""

    pass


# Rate-limited setup view
@method_decorator(
    ratelimit(key="ip", rate=RATE_LIMIT, method=["GET", "POST"], block=True),
    name="dispatch",
)
class RateLimitedSetupView(SetupView):
    """2FA setup view with rate limiting applied."""

    pass


# Rate-limited QR generator view
@method_decorator(
    ratelimit(key="ip", rate=RATE_LIMIT, method=["GET"], block=True),
    name="dispatch",
)
class RateLimitedQRGeneratorView(QRGeneratorView):
    """QR code generator view with rate limiting applied."""

    pass
