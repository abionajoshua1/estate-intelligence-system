from typing import cast

from django.contrib.auth.models import User
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsResident(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user.is_authenticated:
            return False

        user = cast(User, request.user)
        user_profile = getattr(user, "profile", None)
        return getattr(user_profile, "role", None) == "resident"


class IsManager(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user.is_authenticated:
            return False

        user = cast(User, request.user)
        return getattr(getattr(user, "profile", None), "role", None) == "manager"


class IsAdmin(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user.is_authenticated:
            return False

        user_profile = getattr(request.user, "profile", None)
        return getattr(user_profile, "role", None) == "admin"


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user.is_authenticated:
            return False

        user = cast(User, request.user)
        user_profile = getattr(user, "profile", None)
        return getattr(user_profile, "role", None) in ["manager", "admin"]