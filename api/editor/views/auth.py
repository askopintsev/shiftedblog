"""Editor API authentication views."""

from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_otp import login as otp_login
from django_otp import match_token, user_has_device
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.editor.permissions import IsAuthenticatedStaff, IsStaffUser, client_user_is_verified

User = get_user_model()


def _user_payload(user: User, request: Request) -> dict:
    return {
        "id": user.pk,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_verified": client_user_is_verified(request, user),
        "has_2fa": user_has_device(user),
    }


class CsrfView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request) -> Response:
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True))
    def post(self, request: Request) -> Response:
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"ok": False, "error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active or not user.is_staff:
            return Response(
                {"ok": False, "error": "Staff access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        if user_has_device(user):
            return Response(
                {
                    "ok": True,
                    "step": "2fa",
                    "user": _user_payload(user, request),
                },
            )
        return Response(
            {
                "ok": True,
                "step": "complete",
                "user": _user_payload(user, request),
            },
        )


class TwoFactorVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True))
    def post(self, request: Request) -> Response:
        token = (request.data.get("token") or "").strip()
        device = match_token(request.user, token)
        if device is None:
            return Response(
                {"ok": False, "error": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_login(request, device)
        return Response({"ok": True, "user": _user_payload(request.user, request)})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response({"ok": True})


class MeView(APIView):
    permission_classes = [IsAuthenticatedStaff]

    def get(self, request: Request) -> Response:
        return Response({"ok": True, "user": _user_payload(request.user, request)})


class SessionKeepaliveView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request: Request) -> Response:
        request.session.modified = True
        return Response(status=status.HTTP_204_NO_CONTENT)
